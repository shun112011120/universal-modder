package com.sodcraft.client.mixin;

import net.minecraft.client.renderer.special.SpecialModelRenderers;
import net.minecraft.util.ExtraCodecs;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.gen.Accessor;

/** Vanilla keeps the special item renderer types in a private map; this lets the mod add sodcraft:sod2_mesh. */
@Mixin(SpecialModelRenderers.class)
public interface SpecialModelRenderersAccessor {
	@SuppressWarnings("rawtypes")
	@Accessor("ID_MAPPER")
	static ExtraCodecs.LateBoundIdMapper sodcraft$idMapper() {
		throw new AssertionError();
	}
}
