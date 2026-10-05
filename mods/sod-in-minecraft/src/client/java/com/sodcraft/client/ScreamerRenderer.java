package com.sodcraft.client;

import com.sodcraft.SodCraft;
import net.minecraft.client.renderer.entity.EntityRendererProvider;
import net.minecraft.client.renderer.entity.ZombieRenderer;
import net.minecraft.client.renderer.entity.state.ZombieRenderState;
import net.minecraft.resources.Identifier;

/** The zombie model with the Screamer's own skin. */
public class ScreamerRenderer extends ZombieRenderer {
	private static final Identifier TEXTURE = SodCraft.id("textures/entity/screamer.png");

	public ScreamerRenderer(final EntityRendererProvider.Context context) {
		super(context);
	}

	@Override
	public Identifier getTextureLocation(final ZombieRenderState state) {
		return TEXTURE;
	}
}
