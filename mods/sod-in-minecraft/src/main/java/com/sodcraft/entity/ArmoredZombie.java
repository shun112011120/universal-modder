package com.sodcraft.entity;

import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.EquipmentSlot;
import net.minecraft.world.entity.ai.attributes.AttributeSupplier;
import net.minecraft.world.entity.ai.attributes.Attributes;
import net.minecraft.world.entity.monster.zombie.Zombie;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.world.level.Level;

/** A zombie in riot gear: its helmet stops headshot bonuses (see GunItem), so aim for the body or use melee. */
public class ArmoredZombie extends SodZombie {
	public ArmoredZombie(final EntityType<? extends Zombie> type, final Level level) {
		super(type, level, false);
		setItemSlot(EquipmentSlot.HEAD, new ItemStack(Items.IRON_HELMET));
		setItemSlot(EquipmentSlot.CHEST, new ItemStack(Items.IRON_CHESTPLATE));
		setDropChance(EquipmentSlot.HEAD, 0.0F);
		setDropChance(EquipmentSlot.CHEST, 0.0F);
	}

	public static AttributeSupplier.Builder createAttributes() {
		return base().add(Attributes.MAX_HEALTH, 26.0).add(Attributes.ARMOR, 4.0).add(Attributes.ATTACK_DAMAGE, 4.0);
	}
}
