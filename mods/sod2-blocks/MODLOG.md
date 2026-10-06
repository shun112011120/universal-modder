# MODLOG: SoDBlocks (Minecraft blocks inside State of Decay 2)

The owner's direction since 2026-10-06: State of Decay 2 is the base game, and Minecraft-style blocks are added to it
(build, mine). This replaced building SoD2 inside Minecraft (`mods/sod-in-minecraft`, paused at v0.5.0). Solo/offline
play only.

## Setup
- **Game:** State of Decay 2: Juggernaut Edition, Xbox app (Game Pass/MS Store) copy, package
  `Microsoft.Dayton_2.741.435.0_x64__8wekyb3d8bbwe`, installed at `C:\XboxGames\State of Decay 2\Content`. The game exe
  can't be read from outside (encrypted on disk), but the `Binaries\Win64` folder is writable (Authenticated Users:
  Modify) and the game loads a `dwmapi.dll` proxy from it. No anti-cheat found.
- **Loader:** UE4SS experimental-latest (`UE4SS_v3.0.1-1159-g5418fa4e`), from github.com/UE4SS-RE/RE-UE4SS.
- **Install:** `install.ps1` (full, SoD2 closed) or `install.ps1 -Sync` (our files only, then Ctrl+R in game: hot
  reload is on). Remove everything with `uninstall.ps1`.
- **Keys:** F6 places a block, F5 breaks one, F7 writes diagnostics to `Binaries\Win64\ue4ss\UE4SS.log`.

## What SoD2's engine needs (2026-10-06)
SoD2 runs Undead Labs' customised Unreal **4.13** (package files say object version 506, licensee 7), and UE4SS needs
three fixes for it:
1. **EngineVersionOverride 4.14, not 4.13.** With 4.13 (also what UE4SS auto-detects), UE4SS stalls forever at
   "Still waiting for the KismetStringLibrary CDO", so mods never start. With 4.14 it starts.
2. **ProcessEvent.** UE4SS's 4.14 default vtable slot holds a shared `33 C0 C3` (`xor eax,eax; ret`) stub, so every
   function call silently returned 0 or nothing while property reads worked. Found by reading the game's memory
   (read-only, same user): the KismetStringLibrary CDO's vtable has the real `UObject::ProcessEvent` at **slot 53**
   (offset `0x1A8`). It has the classic UE4 prologue
   `40 55 56 57 41 54 41 55 41 56 41 57 48 81 EC F0 00 00 00 48 8D 6C 24 30 48 89 9D 18 01 00 00 48` (unique in the
   module) and tests `UFunction::FunctionFlags` (0x88) for FUNC_Native (0x400).
   - **Fix:** `ue4ss/VTableLayout.ini` with 3 `[UObjectBase]` entries and 52 placeholders before `ProcessEvent` in
     `[UObject]`. UE4SS then logs `UObject::ProcessEvent = 0x1A8`. That's 2 fewer than base + index suggests:
     UE4SS doesn't count the first two slots the way the example configs imply, so check the logged offset.
   - A `UE4SS_Signatures/ProcessEvent.lua` is **ignored** in this build: ProcessEvent comes from the vtable layout.
3. **The player controller.** `UEHelpers.GetPlayerController()` returns nothing. SoD2's controller is
   `VanillaPlayerController_BP_C` (the menu uses `FrontendPlayerController_BP_C`), so the mod tracks it with
   `NotifyOnNewObject` and falls back to `FindAllOf`. The pawn is `HumanCharacter_C`.

## What works and what doesn't (UE4SS on SoD2)
- **Works:** property reads and writes (structs too, e.g. `RootComponent.RelativeLocation`), function calls with
  struct returns after fix 2 (e.g. `K2_GetActorLocation`), `World:SpawnActor`, `SetStaticMesh`, hot reload.
- **No `SetMobility` function:** set `StaticMeshComponent.Mobility = 2` as a property before `SetStaticMesh`, or the
  mesh change is refused on a static component.
- **`LoadAsset` fails** ("asset_registry was nullptr"). Only assets already in memory can be found with
  `StaticFindObject`; `/Engine/BasicShapes/Cube.Cube` is already loaded.
- **Hooks that failed to attach:** `ProcessConsoleExec` and `CallFunctionByNameWithArguments` (UE4SS console
  commands). `pc:ConsoleCommand` isn't callable. SoD2 has its own `DaytonCheatManager_BP_C`, but `Summon` does nothing.
- **First block:** a 1 m cube spawned 3 m in front of the survivor (screenshot sent to the owner), lit and shadowed
  by the game.

## v0.1: place and break (in progress)
- F6: line trace from the camera (`KismetSystemLibrary:LineTraceSingle`, the UE4SS LineTraceMod pattern), place a
  cube in the grid cell just outside the hit face (1 m grid), never inside the player. F5: trace, and destroy the
  block if this mod placed it. Blocks are tracked in memory only (not saved yet).

## Next
Saving blocks per map; block types with textures (SoD2's own materials first; Minecraft textures need a cooked pak
for UE 4.13/4.14); a hotbar/picker; maybe Minecraft-style mining by hitting.
