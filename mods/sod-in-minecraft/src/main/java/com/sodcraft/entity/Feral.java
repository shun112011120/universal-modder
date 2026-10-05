package com.sodcraft.entity;

import net.minecraft.network.chat.Component;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.effect.MobEffectInstance;
import net.minecraft.world.effect.MobEffects;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.ai.attributes.AttributeSupplier;
import net.minecraft.world.entity.ai.attributes.Attributes;
import net.minecraft.world.entity.ai.goal.LeapAtTargetGoal;
import net.minecraft.world.entity.monster.zombie.Zombie;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.level.Level;

/** Fast and agile: it lunges from a few blocks away and pins you (you can barely move for a moment). */
public class Feral extends SodZombie {
	public Feral(final EntityType<? extends Zombie> type, final Level level, final boolean plague) {
		super(type, level, plague);
	}

	public static AttributeSupplier.Builder createAttributes() {
		return base()
			.add(Attributes.MAX_HEALTH, 34.0)
			.add(Attributes.MOVEMENT_SPEED, 0.38)
			.add(Attributes.ATTACK_DAMAGE, 5.0)
			.add(Attributes.FOLLOW_RANGE, 48.0)
			.add(Attributes.KNOCKBACK_RESISTANCE, 0.3);
	}

	@Override
	protected void registerGoals() {
		super.registerGoals();
		goalSelector.addGoal(1, new LeapAtTargetGoal(this, 0.55F));
	}

	@Override
	public boolean doHurtTarget(final ServerLevel level, final Entity target) {
		boolean hit = super.doHurtTarget(level, target);
		if (hit && target instanceof Player player) {
			player.addEffect(new MobEffectInstance(MobEffects.SLOWNESS, 30, 4), this);
			player.sendOverlayMessage(Component.translatable("message.sodcraft.pinned"));
		}

		return hit;
	}
}
