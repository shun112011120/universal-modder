package com.sodcraft.item;

import com.sodcraft.ModContent;
import net.minecraft.network.chat.Component;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.InteractionResult;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.Level;

/** Cures blood plague completely. Made from plague samples that plague zombies drop. */
public class PlagueCureItem extends Item {
	public PlagueCureItem(final Properties properties) {
		super(properties);
	}

	@Override
	public InteractionResult use(final Level level, final Player player, final InteractionHand hand) {
		if (!player.hasEffect(ModContent.BLOOD_PLAGUE)) {
			player.sendOverlayMessage(Component.translatable("message.sodcraft.not_infected"));
			return InteractionResult.FAIL;
		}

		if (!level.isClientSide()) {
			player.removeEffect(ModContent.BLOOD_PLAGUE);
			level.playSound(null, player.getX(), player.getY(), player.getZ(), SoundEvents.HONEY_DRINK, SoundSource.PLAYERS, 1.0F, 1.0F);
			player.sendOverlayMessage(Component.translatable("message.sodcraft.cured"));
			if (!player.getAbilities().instabuild) {
				ItemStack stack = player.getItemInHand(hand);
				stack.shrink(1);
			}
		}

		return InteractionResult.CONSUME;
	}
}
