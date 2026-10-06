-- SoDBlocks: Minecraft-style blocks inside State of Decay 2 (UE4SS Lua mod).
--   F6  place a 1 m block on the grid where the camera points (on the face you aim at)
--   F5  break the block you aim at (only blocks this mod placed)
--   F7  diagnostics (camera, trace, counts) into UE4SS.log
-- SoD2 needs: EngineVersionOverride 4.14 and VTableLayout.ini (ProcessEvent = slot 53); see ../../../MODLOG.md.
local UEHelpers = require("UEHelpers")

local GRID = 100.0        -- Unreal units per block (1 m)
local REACH = 800.0       -- how far you can place/break (8 m)

local function log(msg)
    print("[SoDBlocks] " .. msg .. "\n")
end

local function try(label, fn)
    local ok, err = pcall(fn)
    if not ok then
        log(label .. " failed: " .. tostring(err))
    end
    return ok
end

local function valid(o)
    return o ~= nil and o:IsValid()
end

log("loaded")

-- the player: SoD2's VanillaPlayerController_BP_C isn't found by UEHelpers.GetPlayerController()
local lastController = nil
NotifyOnNewObject("/Script/Engine.PlayerController", function(pc)
    if valid(pc) and not string.find(pc:GetFullName(), "Default__", 1, true) then
        lastController = pc
    end
end)

local function playerController()
    if valid(lastController) then
        return lastController
    end
    for _, pc in ipairs(FindAllOf("PlayerController") or {}) do
        if valid(pc) and not string.find(pc:GetFullName(), "Default__", 1, true) then
            lastController = pc
            return pc
        end
    end
    return nil
end

-- blocks this mod placed: actor full name -> { actor, x, y, z } (grid cell)
local blocks = {}
local cubeMesh = nil

local function mesh()
    if not valid(cubeMesh) then
        cubeMesh = StaticFindObject("/Engine/BasicShapes/Cube.Cube")
    end
    return cubeMesh
end

-- line trace from the camera; returns hit table or nil
local function aim()
    local pc = playerController()
    if not pc then
        log("no player controller")
        return nil
    end
    local pawn = pc.Pawn
    local cam = pc.PlayerCameraManager
    if not valid(pawn) or not valid(cam) then
        log("no pawn or camera")
        return nil
    end
    local ksl = UEHelpers.GetKismetSystemLibrary()
    local kml = UEHelpers.GetKismetMathLibrary()
    local start = cam:GetCameraLocation()
    local dir = kml:GetForwardVector(cam:GetCameraRotation())
    -- third-person camera: start the ray level with the player so it doesn't hit the player's back
    local finish = { X = start.X + dir.X * (REACH + 400), Y = start.Y + dir.Y * (REACH + 400), Z = start.Z + dir.Z * (REACH + 400) }
    -- UE 4.13 calls it LineTraceSingle_NEW (no colour parameters); newer engines LineTraceSingle
    local color = { R = 0, G = 0, B = 0, A = 0 }
    local attempts = {
        { "LineTraceSingle_NEW+colors", function(hit) return ksl:LineTraceSingle_NEW(pawn, start, finish, 0, false, {}, 0, hit, true, color, color, 0.0) end },
        { "LineTraceSingle_NEW", function(hit) return ksl:LineTraceSingle_NEW(pawn, start, finish, 0, false, {}, 0, hit, true) end },
    }
    for _, attempt in ipairs(attempts) do
        local hit = {}
        local ok, was = pcall(attempt[2], hit)
        if ok then
            if not was then
                return nil
            end
            return { hit = hit, pawn = pawn, pc = pc }
        end
        log(attempt[1] .. " failed: " .. tostring(was))
    end
    return nil
end

local function cellOf(x, y, z)
    return math.floor(x / GRID), math.floor(y / GRID), math.floor(z / GRID)
end

local function hitActor(hit)
    local a
    try("HitResult.Actor", function() a = hit.Actor:Get() end)
    return a
end

local function place()
    local r = aim()
    if not r then
        log("place: nothing in reach")
        return
    end
    local p, n = r.hit.ImpactPoint, r.hit.ImpactNormal
    -- the cell just outside the face that was hit
    local cx, cy, cz = cellOf(p.X + n.X * GRID * 0.5, p.Y + n.Y * GRID * 0.5, p.Z + n.Z * GRID * 0.5)
    local pos = { X = (cx + 0.5) * GRID, Y = (cy + 0.5) * GRID, Z = (cz + 0.5) * GRID }

    -- not inside the player
    local me = r.pawn:K2_GetActorLocation()
    if math.abs(me.X - pos.X) < 80 and math.abs(me.Y - pos.Y) < 80 and math.abs(me.Z - pos.Z) < 140 then
        log("place: that's where you're standing")
        return
    end
    for _, b in pairs(blocks) do
        if b.x == cx and b.y == cy and b.z == cz and valid(b.actor) then
            log("place: already a block there")
            return
        end
    end

    local world = r.pawn:GetWorld()
    local actor
    try("SpawnActor", function()
        actor = world:SpawnActor(StaticFindObject("/Script/Engine.StaticMeshActor"), pos, { Pitch = 0, Yaw = 0, Roll = 0 })
    end)
    if not valid(actor) then
        log("place: spawn failed")
        return
    end
    local comp = actor.StaticMeshComponent
    try("Mobility", function() comp.Mobility = 2 end)   -- SoD2 has no SetMobility(); movable lets the mesh change
    try("SetStaticMesh", function() comp:SetStaticMesh(mesh()) end)
    blocks[actor:GetFullName()] = { actor = actor, x = cx, y = cy, z = cz }
    log(string.format("placed block at cell %d %d %d", cx, cy, cz))
end

local function breakBlock()
    local r = aim()
    if not r then
        log("break: nothing in reach")
        return
    end
    local a = hitActor(r.hit)
    if not valid(a) then
        log("break: hit has no actor")
        return
    end
    local key = a:GetFullName()
    local b = blocks[key]
    if not b then
        log("break: not one of our blocks (" .. key .. ")")
        return
    end
    try("K2_DestroyActor", function() a:K2_DestroyActor() end)
    blocks[key] = nil
    log(string.format("broke block at cell %d %d %d", b.x, b.y, b.z))
end

local function listFunctions(path, pattern)
    local class = StaticFindObject(path)
    if not valid(class) then
        log("diag: no class " .. path)
        return
    end
    local names = {}
    try("ForEachFunction", function()
        class:ForEachFunction(function(fn)
            local n = fn:GetFName():ToString()
            if string.find(string.lower(n), pattern, 1, true) then
                names[#names + 1] = n
            end
        end)
    end)
    log("diag: " .. path .. " functions with '" .. pattern .. "': " .. table.concat(names, ", "))
end

local function diagnose()
    local pc = playerController()
    local cam = pc and pc.PlayerCameraManager
    if valid(cam) then
        try("camera", function()
            local s = cam:GetCameraLocation()
            local rot = cam:GetCameraRotation()
            log(string.format("diag: camera at %s %s %s, rotation P %s Y %s R %s", tostring(s.X), tostring(s.Y), tostring(s.Z),
                tostring(rot.Pitch), tostring(rot.Yaw), tostring(rot.Roll)))
            local d = UEHelpers.GetKismetMathLibrary():GetForwardVector(rot)
            log(string.format("diag: forward %s %s %s", tostring(d.X), tostring(d.Y), tostring(d.Z)))
        end)
        try("camera cache", function()
            local pov = cam.CameraCache.POV
            log(string.format("diag: CameraCache.POV rotation P %s Y %s", tostring(pov.Rotation.Pitch), tostring(pov.Rotation.Yaw)))
        end)
    end
    local r = aim()
    local count = 0
    for _ in pairs(blocks) do
        count = count + 1
    end
    log("diag: our blocks " .. count)
    if r then
        local p = r.hit.ImpactPoint
        local a = hitActor(r.hit)
        log(string.format("diag: aim hits %.0f %.0f %.0f on %s", p.X, p.Y, p.Z, valid(a) and a:GetFullName() or "?"))
    else
        log("diag: aim hits nothing")
    end
end

local function key(k, fn, label)
    RegisterKeyBind(k, function()
        ExecuteInGameThread(function()
            try(label, fn)
        end)
    end)
end

-- F8: level the camera (pitch 0, keep yaw)
local function levelView()
    local pc = playerController()
    if not pc then
        return
    end
    local r = pc:GetControlRotation()
    pc:SetControlRotation({ Pitch = -5.0, Yaw = r.Yaw, Roll = 0.0 })
    log(string.format("view levelled (yaw %.0f)", r.Yaw))
end

key(Key.F8, levelView, "levelView")
key(Key.F6, place, "place")
key(Key.F5, breakBlock, "break")
key(Key.F7, diagnose, "diagnose")
