package com.sodcraft;

import com.sodcraft.block.PlagueHeartBlock;
import com.sodcraft.block.PlagueHeartBlockEntity;
import com.sodcraft.entity.Screamer;
import com.sodcraft.item.GunItem;
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

	public static final Item PISTOL_AMMO = item("pistol_ammo", Item::new, new Item.Properties());
	public static final Item RIFLE_AMMO = item("rifle_ammo", Item::new, new Item.Properties());

	/** Quick and quiet-ish: 12 rounds, 5 damage (12.5 headshot), zombies hear it 32 blocks away. */
	public static final Item PISTOL = item("pistol", p -> new GunItem(new GunItem.Stats(12, 5.0F, 48.0, 5, 30, 32.0, 2.5F, 1.2F, 1.6F),
		() -> ModContent.PISTOL_AMMO, p), new Item.Properties());

	/** Hard-hitting and loud: 5 rounds, 12 damage (30 headshot), zombies hear it 56 blocks away. */
	public static final Item RIFLE = item("rifle", p -> new GunItem(new GunItem.Stats(5, 12.0F, 96.0, 20, 50, 56.0, 6.0F, 0.3F, 0.8F),
		() -> ModContent.RIFLE_AMMO, p), new Item.Properties());

	private ModContent() {
	}

	private static Item item(final String name, final java.util.function.Function<Item.Properties, Item> factory, final Item.Properties properties) {
		ResourceKey<Item> key = ResourceKey.create(Registries.ITEM, SodCraft.id(name));
		return Registry.register(BuiltInRegistries.ITEM, key, factory.apply(properties.setId(key)));
	}

	/** Loads this class, which registers everything above. */
	static void init() {
	}
}
