package com.sodcraft.entity;

import com.sodcraft.SodCraft;
import java.util.List;
import net.minecraft.core.particles.ParticleTypes;
import net.minecraft.network.chat.Component;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;
import net.minecraft.world.effect.MobEffectInstance;
import net.minecraft.world.effect.MobEffects;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.ai.attributes.AttributeInstance;
import net.minecraft.world.entity.ai.attributes.AttributeSupplier;
import net.minecraft.world.entity.ai.attributes.Attributes;
import net.minecraft.world.entity.monster.zombie.Zombie;
import net.minecraft.world.entity.monster.zombie.ZombifiedPiglin;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.level.Level;

/**
 * A weak zombie that screams when it sees you: every zombie within CALL_RANGE comes for you, and if you're close the
 * scream staggers you (slowness + nausea). Then it needs SCREAM_COOLDOWN ticks to recover.
 */
public class Screamer extends Zombie {
	private static final double SEE_RANGE = 24.0;
	private static final double CALL_RANGE = 40.0;
	private static final double STAGGER_RANGE = 10.0;
	private static final int SCREAM_COOLDOWN = 200; // 10 s

	private int screamCooldown = 40;

	public Screamer(final EntityType<? extends Zombie> type, final Level level) {
		super(type, level);
	}

	public static AttributeSupplier.Builder createAttributes() {
		return Zombie.createAttributes()
			.add(Attributes.MAX_HEALTH, 14.0)
			.add(Attributes.ATTACK_DAMAGE, 1.0)
			.add(Attributes.MOVEMENT_SPEED, 0.2)
			.add(Attributes.FOLLOW_RANGE, SEE_RANGE + 8.0);
	}

	@Override
	protected void customServerAiStep(final ServerLevel level) {
		super.customServerAiStep(level);
		if (screamCooldown > 0) {
			screamCooldown--;
			return;
		}

		if (getTarget() instanceof Player player && player.isAlive() && distanceToSqr(player) < SEE_RANGE * SEE_RANGE && hasLineOfSight(player)) {
			scream(level, player);
			screamCooldown = SCREAM_COOLDOWN;
		}
	}

	private void scream(final ServerLevel level, final Player player) {
		level.playSound(null, getX(), getY(), getZ(), SoundEvents.GHAST_SCREAM, SoundSource.HOSTILE, 4.0F, 0.6F);
		level.sendParticles(ParticleTypes.SONIC_BOOM, getX(), getEyeY(), getZ(), 1, 0.0, 0.0, 0.0, 0.0);

		List<Zombie> horde = level.getEntitiesOfClass(Zombie.class, getBoundingBox().inflate(CALL_RANGE),
			z -> z != this && z.isAlive() && !(z instanceof ZombifiedPiglin));
		for (Zombie z : horde) {
			AttributeInstance follow = z.getAttribute(Attributes.FOLLOW_RANGE);
			if (follow != null && follow.getBaseValue() < CALL_RANGE + 8.0) {
				follow.setBaseValue(CALL_RANGE + 8.0); // or they lose interest before they arrive
			}

			z.setTarget(player);
			z.addEffect(new MobEffectInstance(MobEffects.SPEED, 200, 0));
		}

		if (distanceToSqr(player) < STAGGER_RANGE * STAGGER_RANGE) {
			player.addEffect(new MobEffectInstance(MobEffects.SLOWNESS, 60, 2), this);
			player.addEffect(new MobEffectInstance(MobEffects.NAUSEA, 80, 0), this);
		}

		player.sendOverlayMessage(Component.translatable("message.sodcraft.scream", horde.size()));
		SodCraft.LOG.info("screamer at {} called {} zombies", blockPosition().toShortString(), horde.size());
	}

	/** Screamers stay screamers underwater (zombies would turn into drowned). */
	@Override
	protected boolean convertsInWater() {
		return false;
	}
}
