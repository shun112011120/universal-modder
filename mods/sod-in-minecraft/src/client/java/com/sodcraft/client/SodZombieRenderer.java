package com.sodcraft.client;

import com.sodcraft.SodCraft;
import net.minecraft.client.renderer.entity.EntityRendererProvider;
import net.minecraft.client.renderer.entity.ZombieRenderer;
import net.minecraft.client.renderer.entity.state.ZombieRenderState;
import net.minecraft.resources.Identifier;

/** The zombie model with one of SoDcraft's skins (textures/entity/<name>.png). Size comes from the SCALE attribute. */
public class SodZombieRenderer extends ZombieRenderer {
	private final Identifier texture;

	public SodZombieRenderer(final EntityRendererProvider.Context context, final String skin) {
		super(context);
		this.texture = SodCraft.id("textures/entity/" + skin + ".png");
	}

	@Override
	public Identifier getTextureLocation(final ZombieRenderState state) {
		return texture;
	}
}
