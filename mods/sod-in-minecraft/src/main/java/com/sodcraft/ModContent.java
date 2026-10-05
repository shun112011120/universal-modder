package com.sodcraft;

import com.sodcraft.block.PlagueHeartBlock;
import com.sodcraft.block.PlagueHeartBlockEntity;
import com.sodcraft.entity.Screamer;
import net.fabricmc.fabric.api.object.builder.v1.block.entity.FabricBlockEntityTypeBuilder;
import net.minecraft.core.Registry;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.core.registries.Registries;
import net.minecraft.resources.ResourceKey;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.MobCategory;
import net.minecraft.world.item.BlockItem;
import net.minecraft.world.item.Item;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.SoundType;
import net.minecraft.world.level.block.entity.BlockEntityType;
import net.minecraft.world.level.block.state.BlockBehaviour;

/** Everything the mod registers. Order matters: the block entity type needs the block. */
public final class ModContent {
	private static final ResourceKey<Block> PLAGUE_HEART_KEY = ResourceKey.create(Registries.BLOCK, SodCraft.id("plague_heart"));
	private static final ResourceKey<Item> PLAGUE_HEART_ITEM_KEY = ResourceKey.create(Registries.ITEM, SodCraft.id("plague_heart"));
	private static final ResourceKey<EntityType<?>> SCREAMER_KEY = ResourceKey.create(Registries.ENTITY_TYPE, SodCraft.id("screamer"));

	/** Fleshy and glowing; an axe cuts it fastest, TNT works too (blast resistance of stone). */
	public static final Block PLAGUE_HEART = Registry.register(BuiltInRegistries.BLOCK, PLAGUE_HEART_KEY,
		new PlagueHeartBlock(BlockBehaviour.Properties.of()
			.setId(PLAGUE_HEART_KEY)
			.strength(5.0F, 6.0F)
			.sound(SoundType.WART_BLOCK)
			.lightLevel(state -> 6)));

	public static final Item PLAGUE_HEART_ITEM = Registry.register(BuiltInRegistries.ITEM, PLAGUE_HEART_ITEM_KEY,
		new BlockItem(PLAGUE_HEART, new Item.Properties().setId(PLAGUE_HEART_ITEM_KEY).useBlockDescriptionPrefix()));

	public static final BlockEntityType<PlagueHeartBlockEntity> PLAGUE_HEART_BE = Registry.register(BuiltInRegistries.BLOCK_ENTITY_TYPE,
		SodCraft.id("plague_heart"), FabricBlockEntityTypeBuilder.create(PlagueHeartBlockEntity::new, PLAGUE_HEART).build());

	public static final EntityType<Screamer> SCREAMER = Registry.register(BuiltInRegistries.ENTITY_TYPE, SCREAMER_KEY,
		EntityType.Builder.<Screamer>of(Screamer::new, MobCategory.MONSTER)
			.sized(0.6F, 1.95F)
			.eyeHeight(1.74F)
			.clientTrackingRange(8)
			.build(SCREAMER_KEY));

	private ModContent() {
	}

	/** Loads this class, which registers everything above. */
	static void init() {
	}
}
