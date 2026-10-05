package com.sodcraft.entity;

import net.minecraft.core.particles.ParticleTypes;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;
import net.minecraft.world.damagesource.DamageSource;
import net.minecraft.world.effect.MobEffectInstance;
import net.minecraft.world.effect.MobEffects;
import net.minecraft.world.entity.AreaEffectCloud;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.ai.attributes.AttributeSupplier;
import net.minecraft.world.entity.ai.attributes.Attributes;
import net.minecraft.world.entity.monster.zombie.Zombie;
import net.minecraft.world.level.Level;

/**
 * Slow and swollen. When it gets close it bursts, and it bursts when killed too: a toxic cloud (poison + nausea)
 * hangs there for 10 s. Shoot it from a distance.
 */
public class Bloater extends SodZombie {
	private static final double BURST_RANGE = 2.2;
	private boolean burst;

	public Bloater(final EntityType<? extends Zombie> type, final Level level) {
		super(type, level, false);
	}

	public static AttributeSupplier.Builder createAttributes() {
		return base()
			.add(Attributes.MAX_HEALTH, 12.0)
			.add(Attributes.MOVEMENT_SPEED, 0.17)
			.add(Attributes.ATTACK_DAMAGE, 1.0)
			.add(Attributes.SCALE, 1.25);
	}

	@Override
	protected void customServerAiStep(final ServerLevel level) {
		super.customServerAiStep(level);
		if (!burst && getTarget() != null && getTarget().isAlive() && distanceToSqr(getTarget()) < BURST_RANGE * BURST_RANGE) {
			burst(level);
			kill(level);
		}
	}

	@Override
	public void die(final DamageSource source) {
		super.die(source);
		if (!burst && level() instanceof ServerLevel level) {
			burst(level);
		}
	}

	private void burst(final ServerLevel level) {
		burst = true;
		AreaEffectCloud cloud = new AreaEffectCloud(level, getX(), getY() + 0.3, getZ());
		cloud.setOwner(this);
		cloud.setRadius(4.0F);
		cloud.setRadiusPerTick(-0.005F);
		cloud.setWaitTime(0);
		cloud.setDuration(200);
		cloud.addEffect(new MobEffectInstance(MobEffects.POISON, 100, 1));
		cloud.addEffect(new MobEffectInstance(MobEffects.NAUSEA, 160, 0));
		level.addFreshEntity(cloud);
		level.sendParticles(ParticleTypes.SNEEZE, getX(), getY() + 1.0, getZ(), 40, 1.2, 0.8, 1.2, 0.02);
		level.playSound(null, getX(), getY(), getZ(), SoundEvents.PUFFER_FISH_BLOW_UP, SoundSource.HOSTILE, 2.0F, 0.5F);
		level.playSound(null, getX(), getY(), getZ(), SoundEvents.SLIME_DEATH, SoundSource.HOSTILE, 2.0F, 0.6F);
	}
}
