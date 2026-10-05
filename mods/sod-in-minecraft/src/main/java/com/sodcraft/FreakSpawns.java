package com.sodcraft;

import com.sodcraft.block.PlagueHeartBlockEntity;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.util.RandomSource;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.EntitySpawnReason;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.monster.zombie.Zombie;

/**
 * Freaks among the dead, the way State of Decay 2 mixes them in: the first time a vanilla zombie loads (natural
 * spawn, spawner, command), it may be swapped for a SoD2 type. It's marked so it's only rolled once.
 */
final class FreakSpawns {
	private static final String ROLLED = "sodcraft_rolled";

	private FreakSpawns() {
	}

	static void onEntityLoad(final Entity entity, final ServerLevel level) {
		if (entity.getClass() != Zombie.class || entity.entityTags().contains(ROLLED) || entity.entityTags().contains(PlagueHeartBlockEntity.HEART_TAG)) {
			return;
		}

		entity.addTag(ROLLED);
		EntityType<? extends Zombie> type = roll(level.getRandom());
		if (type != null) {
			// not while the level is adding entities: next tick
			level.getServer().execute(() -> replace(level, (Zombie) entity, type));
		}
	}

	/** Per 1000 vanilla zombies. */
	private static EntityType<? extends Zombie> roll(final RandomSource random) {
		int r = random.nextInt(1000);
		if ((r -= 90) < 0) {
			return ModContent.PLAGUE_ZOMBIE;
		}
		if ((r -= 30) < 0) {
			return ModContent.SCREAMER;
		}
		if ((r -= 30) < 0) {
			return ModContent.BLOATER;
		}
		if ((r -= 25) < 0) {
			return ModContent.FERAL;
		}
		if ((r -= 25) < 0) {
			return ModContent.ARMORED_ZOMBIE;
		}
		if ((r -= 8) < 0) {
			return ModContent.JUGGERNAUT;
		}
		if ((r -= 6) < 0) {
			return ModContent.PLAGUE_FERAL;
		}
		if ((r -= 3) < 0) {
			return ModContent.PLAGUE_JUGGERNAUT;
		}
		return null;
	}

	private static void replace(final ServerLevel level, final Zombie zombie, final EntityType<? extends Zombie> type) {
		if (zombie.isRemoved()) {
			return;
		}

		Zombie freak = type.create(level, EntitySpawnReason.CONVERSION);
		if (freak == null) {
			return;
		}

		freak.snapTo(zombie.getX(), zombie.getY(), zombie.getZ(), zombie.getYRot(), zombie.getXRot());
		freak.addTag(ROLLED);
		if (zombie.isPersistenceRequired()) {
			freak.setPersistenceRequired();
		}

		if (level.addFreshEntity(freak)) {
			zombie.discard();
		}
	}
}
