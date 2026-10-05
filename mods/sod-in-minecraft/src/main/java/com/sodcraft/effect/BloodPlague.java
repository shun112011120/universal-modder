package com.sodcraft.effect;

import com.sodcraft.ModContent;
import net.minecraft.network.chat.Component;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.effect.MobEffect;
import net.minecraft.world.effect.MobEffectCategory;
import net.minecraft.world.effect.MobEffectInstance;
import net.minecraft.world.effect.MobEffects;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.player.Player;

/**
 * Blood plague: every hit from a plague zombie raises it 20% (amplifier 0..4 = 20..100%). It worsens as it rises:
 * 60% hunger, 80% slowness and weakness, 100% it eats your health until you take a plague cure.
 */
public class BloodPlague extends MobEffect {
	public static final int MAX = 4;

	public BloodPlague() {
		super(MobEffectCategory.HARMFUL, 0x8A0F1C);
	}

	@Override
	public boolean shouldApplyEffectTickThisTick(final int duration, final int amplifier) {
		return duration % 40 == 0;
	}

	@Override
	public boolean applyEffectTick(final ServerLevel level, final LivingEntity entity, final int amplifier) {
		if (amplifier >= 2) {
			entity.addEffect(new MobEffectInstance(MobEffects.HUNGER, 60, 0, false, false));
		}

		if (amplifier >= 3) {
			entity.addEffect(new MobEffectInstance(MobEffects.SLOWNESS, 60, 0, false, false));
			entity.addEffect(new MobEffectInstance(MobEffects.WEAKNESS, 60, 0, false, false));
		}

		if (amplifier >= MAX) {
			entity.hurtServer(level, level.damageSources().magic(), 1.5F);
		}

		return true;
	}

	/** A plague hit: players only (zombies are already sick), not in creative. */
	public static void infect(final LivingEntity target) {
		if (!(target instanceof Player player) || player.isCreative() || player.isSpectator()) {
			return;
		}

		MobEffectInstance current = player.getEffect(ModContent.BLOOD_PLAGUE);
		int level = current == null ? 0 : Math.min(MAX, current.getAmplifier() + 1);
		player.addEffect(new MobEffectInstance(ModContent.BLOOD_PLAGUE, 12000, level));
		player.sendOverlayMessage(Component.translatable(level >= MAX ? "message.sodcraft.plague_full" : "message.sodcraft.plague", (level + 1) * 20));
	}
}
