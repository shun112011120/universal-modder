package com.sodcraft;

import com.sodcraft.entity.Screamer;
import net.fabricmc.api.ModInitializer;
import net.fabricmc.fabric.api.object.builder.v1.entity.FabricDefaultAttributeRegistry;
import net.minecraft.resources.Identifier;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/** State of Decay 2 ideas, rebuilt from scratch: Plague Hearts and Screamers. */
public class SodCraft implements ModInitializer {
	public static final String ID = "sodcraft";
	public static final Logger LOG = LoggerFactory.getLogger(ID);

	public static Identifier id(final String path) {
		return Identifier.fromNamespaceAndPath(ID, path);
	}

	@Override
	public void onInitialize() {
		ModContent.init();
		FabricDefaultAttributeRegistry.register(ModContent.SCREAMER, Screamer.createAttributes());
		LOG.info("sodcraft loaded: plague_heart, screamer");
	}
}
