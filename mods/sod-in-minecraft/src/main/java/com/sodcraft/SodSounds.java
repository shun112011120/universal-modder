package com.sodcraft;

import net.minecraft.core.Registry;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.resources.Identifier;
import net.minecraft.sounds.SoundEvent;

/**
 * SoDcraft's sound events. The jar's sounds.json points each one at a vanilla sound; the local "SoD2 Assets" pack
 * (tools/sod2_sounds.py) replaces them with State of Decay 2's own recordings.
 */
public final class SodSounds {
	public static final SoundEvent DRY_FIRE = register("gun.dryfire");
	public static final SoundEvent SCREAMER_SCREAM = register("screamer.scream");
	public static final SoundEvent SCREAMER_AMBIENT = register("screamer.ambient");
	public static final SoundEvent SCREAMER_HURT = register("screamer.hurt");
	public static final SoundEvent SCREAMER_DEATH = register("screamer.death");
	public static final SoundEvent BLOATER_AMBIENT = register("bloater.ambient");
	public static final SoundEvent BLOATER_BURST = register("bloater.burst");
	public static final SoundEvent BLOATER_HURT = register("bloater.hurt");
	public static final SoundEvent FERAL_AMBIENT = register("feral.ambient");
	public static final SoundEvent FERAL_ATTACK = register("feral.attack");
	public static final SoundEvent FERAL_HURT = register("feral.hurt");
	public static final SoundEvent FERAL_DEATH = register("feral.death");
	public static final SoundEvent JUGGERNAUT_ATTACK = register("juggernaut.attack");

	private SodSounds() {
	}

	public static SoundEvent register(final String name) {
		Identifier id = SodCraft.id(name);
		return Registry.register(BuiltInRegistries.SOUND_EVENT, id, SoundEvent.createVariableRangeEvent(id));
	}

	static void init() {
	}
}
