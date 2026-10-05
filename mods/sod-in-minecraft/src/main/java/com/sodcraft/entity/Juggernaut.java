package com.sodcraft.entity;

import net.minecraft.network.chat.Component;
import net.minecraft.server.level.ServerLevel;
import com.sodcraft.SodSounds;
import net.minecraft.sounds.SoundSource;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.ai.attributes.AttributeSupplier;
import net.minecraft.world.entity.ai.attributes.Attributes;
import net.minecraft.world.entity.monster.zombie.Zombie;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.level.Level;
import net.minecraft.world.phys.Vec3;

/** Huge and armoured: soaks up a magazine, can't be knocked back, and grabs and throws you when it hits. */
public class Juggernaut extends SodZombie {
	public Juggernaut(final EntityType<? extends Zombie> type, final Level level, final boolean plague) {
		super(type, level, plague);
	}

	public static AttributeSupplier.Builder createAttributes() {
		return base()
			.add(Attributes.MAX_HEALTH, 150.0)
			.add(Attributes.MOVEMENT_SPEED, 0.21)
			.add(Attributes.ATTACK_DAMAGE, 10.0)
			.add(Attributes.ARMOR, 10.0)
			.add(Attributes.KNOCKBACK_RESISTANCE, 1.0)
			.add(Attributes.SCALE, 1.7);
	}

	@Override
	public boolean doHurtTarget(final ServerLevel level, final Entity target) {
		boolean hit = super.doHurtTarget(level, target);
		if (hit) {
			Vec3 away = new Vec3(target.getX() - getX(), 0.0, target.getZ() - getZ());
			away = away.lengthSqr() < 1.0E-4 ? getLookAngle().multiply(1.0, 0.0, 1.0) : away;
			away = away.normalize();
			target.setDeltaMovement(away.x * 1.8, 0.85, away.z * 1.8);
			target.needsSync = true;
			level.playSound(null, getX(), getY(), getZ(), SodSounds.JUGGERNAUT_ATTACK, SoundSource.HOSTILE, 2.0F, 1.0F);
			if (target instanceof Player player) {
				player.sendOverlayMessage(Component.translatable("message.sodcraft.thrown"));
			}
		}

		return hit;
	}
}
