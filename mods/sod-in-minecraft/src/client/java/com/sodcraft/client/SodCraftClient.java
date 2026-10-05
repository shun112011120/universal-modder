package com.sodcraft.client;

import com.sodcraft.ModContent;
import net.fabricmc.api.ClientModInitializer;
import net.fabricmc.fabric.api.client.rendering.v1.EntityRendererRegistry;

public class SodCraftClient implements ClientModInitializer {
	@Override
	public void onInitializeClient() {
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
