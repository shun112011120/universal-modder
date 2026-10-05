package com.sodcraft.client;

import com.sodcraft.ModContent;
import net.fabricmc.api.ClientModInitializer;
import net.fabricmc.fabric.api.client.rendering.v1.EntityRendererRegistry;

public class SodCraftClient implements ClientModInitializer {
	@Override
	public void onInitializeClient() {
		EntityRendererRegistry.register(ModContent.SCREAMER, ScreamerRenderer::new);
	}
}
