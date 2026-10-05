package com.sodcraft.client;

import com.sodcraft.ModContent;
import com.sodcraft.SodCraft;
import com.sodcraft.client.mixin.SpecialModelRenderersAccessor;
import net.fabricmc.api.ClientModInitializer;
import net.fabricmc.fabric.api.client.rendering.v1.EntityRendererRegistry;

public class SodCraftClient implements ClientModInitializer {
	@Override
	@SuppressWarnings("unchecked")
	public void onInitializeClient() {
		// SoD2's own gun meshes (from the local SoD2 Assets pack, made by tools/sod2_import.py)
		SpecialModelRenderersAccessor.sodcraft$idMapper().put(SodCraft.id("sod2_mesh"), Sod2MeshRenderer.Unbaked.CODEC);
		EntityRendererRegistry.register(ModContent.SCREAMER, ScreamerRenderer::new);
		EntityRendererRegistry.register(ModContent.PLAGUE_ZOMBIE, c -> new SodZombieRenderer(c, "plague_zombie"));
		EntityRendererRegistry.register(ModContent.FERAL, c -> new SodZombieRenderer(c, "feral"));
		EntityRendererRegistry.register(ModContent.PLAGUE_FERAL, c -> new SodZombieRenderer(c, "plague_feral"));
		EntityRendererRegistry.register(ModContent.BLOATER, c -> new SodZombieRenderer(c, "bloater"));
		EntityRendererRegistry.register(ModContent.JUGGERNAUT, c -> new SodZombieRenderer(c, "juggernaut"));
		EntityRendererRegistry.register(ModContent.PLAGUE_JUGGERNAUT, c -> new SodZombieRenderer(c, "plague_juggernaut"));
		EntityRendererRegistry.register(ModContent.ARMORED_ZOMBIE, c -> new SodZombieRenderer(c, "armored_zombie"));
	}
}
