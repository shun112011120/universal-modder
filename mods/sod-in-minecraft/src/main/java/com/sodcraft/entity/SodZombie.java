package com.sodcraft.entity;

import com.sodcraft.effect.BloodPlague;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.ai.attributes.AttributeSupplier;
import net.minecraft.world.entity.ai.attributes.Attributes;
import net.minecraft.world.entity.monster.zombie.Zombie;
import net.minecraft.world.level.Level;

/**
 * State of Decay 2's zombies: they don't burn in daylight, don't drown into something else, are never babies and
 * don't call vanilla reinforcements. Plague variants (red eyes) give the player blood plague with every hit.
 */
public class SodZombie extends Zombie {
	private final boolean plague;

	public SodZombie(final EntityType<? extends Zombie> type, final Level level, final boolean plague) {
		super(type, level);
		this.plague = plague;
	}

	public boolean isPlague() {
		return plague;
	}

	/** The plague zombie: a little tougher than a normal one. */
	public static AttributeSupplier.Builder plagueAttributes() {
		return base().add(Attributes.MAX_HEALTH, 26.0).add(Attributes.ATTACK_DAMAGE, 4.0);
	}

	static AttributeSupplier.Builder base() {
		return Zombie.createAttributes().add(Attributes.FOLLOW_RANGE, 40.0).add(Attributes.SPAWN_REINFORCEMENTS_CHANCE, 0.0);
	}

	@Override
	public boolean doHurtTarget(final ServerLevel level, final Entity target) {
		boolean hit = super.doHurtTarget(level, target);
		if (hit && plague && target instanceof LivingEntity living) {
			BloodPlague.infect(living);
		}

		return hit;
	}

	@Override
	protected boolean convertsInWater() {
		return false;
	}

	@Override
	protected boolean isSunSensitive() {
		return false;
	}

	@Override
	public void setBaby(final boolean baby) {
		// never babies
	}
}
