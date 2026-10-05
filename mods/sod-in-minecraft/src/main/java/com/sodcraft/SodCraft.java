package com.sodcraft;

import com.sodcraft.entity.ArmoredZombie;
import com.sodcraft.entity.Bloater;
import com.sodcraft.entity.Feral;
import com.sodcraft.entity.Juggernaut;
import com.sodcraft.entity.Screamer;
import com.sodcraft.entity.SodZombie;
import net.fabricmc.fabric.api.event.lifecycle.v1.ServerEntityEvents;
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
		SodSounds.init();
		ModContent.init();
		FabricDefaultAttributeRegistry.register(ModContent.SCREAMER, Screamer.createAttributes());
		FabricDefaultAttributeRegistry.register(ModContent.PLAGUE_ZOMBIE, SodZombie.plagueAttributes());
		FabricDefaultAttributeRegistry.register(ModContent.FERAL, Feral.createAttributes());
		FabricDefaultAttributeRegistry.register(ModContent.PLAGUE_FERAL, Feral.createAttributes());
		FabricDefaultAttributeRegistry.register(ModContent.BLOATER, Bloater.createAttributes());
		FabricDefaultAttributeRegistry.register(ModContent.JUGGERNAUT, Juggernaut.createAttributes());
		FabricDefaultAttributeRegistry.register(ModContent.PLAGUE_JUGGERNAUT, Juggernaut.createAttributes());
		FabricDefaultAttributeRegistry.register(ModContent.ARMORED_ZOMBIE, ArmoredZombie.createAttributes());
		ServerEntityEvents.ENTITY_LOAD.register(FreakSpawns::onEntityLoad);
		LOG.info("sodcraft loaded: plague heart, guns, blood plague, 9 zombie types");
	}
}
