package com.sodcraft.block;

import com.sodcraft.ModContent;
import com.sodcraft.SodCraft;
import net.minecraft.core.BlockPos;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.BaseEntityBlock;
import net.minecraft.world.level.block.entity.BlockEntity;
import net.minecraft.world.level.block.entity.BlockEntityTicker;
import net.minecraft.world.level.block.entity.BlockEntityType;
import net.minecraft.world.level.block.state.BlockState;

/** A Plague Heart: sends zombie waves at night while a player is near, and fights back when hit. */
public class PlagueHeartBlock extends BaseEntityBlock {
	public PlagueHeartBlock(final Properties properties) {
		super(properties);
	}

	@Override
	public BlockEntity newBlockEntity(final BlockPos pos, final BlockState state) {
		return new PlagueHeartBlockEntity(pos, state);
	}

	@Override
	public <T extends BlockEntity> BlockEntityTicker<T> getTicker(final Level level, final BlockState state, final BlockEntityType<T> type) {
		return level.isClientSide() ? null : createTickerHelper(type, ModContent.PLAGUE_HEART_BE, PlagueHeartBlockEntity::serverTick);
	}

	@Override
	public void setPlacedBy(final Level level, final BlockPos pos, final BlockState state, final LivingEntity placer, final ItemStack stack) {
		super.setPlacedBy(level, pos, state, placer, stack);
		if (!level.isClientSide()) {
			SodCraft.LOG.info("plague heart placed at {} (dark outside: {})", pos.toShortString(), level.isDarkOutside());
		}
	}

	/** A player started hitting it. */
	@Override
	protected void attack(final BlockState state, final Level level, final BlockPos pos, final Player player) {
		super.attack(state, level, pos, player);
		if (level instanceof ServerLevel serverLevel && level.getBlockEntity(pos) instanceof PlagueHeartBlockEntity heart) {
			heart.defend(serverLevel, player);
		}
	}
}
