package com.sodcraft;

import com.sodcraft.block.PlagueHeartBlock;
import com.sodcraft.block.PlagueHeartBlockEntity;
import com.sodcraft.effect.BloodPlague;
import com.sodcraft.entity.ArmoredZombie;
import com.sodcraft.entity.Bloater;
import com.sodcraft.entity.Feral;
import com.sodcraft.entity.Juggernaut;
import com.sodcraft.entity.Screamer;
import com.sodcraft.entity.SodZombie;
import com.sodcraft.item.PlagueCureItem;
import com.sodcraft.item.GunItem;
import net.fabricmc.fabric.api.object.builder.v1.block.entity.FabricBlockEntityTypeBuilder;
import net.minecraft.core.Holder;
import net.minecraft.core.Registry;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.core.registries.Registries;
import net.minecraft.resources.ResourceKey;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.MobCategory;
import net.minecraft.world.effect.MobEffect;
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

	// ammo by calibre (pistol_ammo = .45 ACP and rifle_ammo = .30-06 keep their ids from v0.2)
	public static final Item PISTOL_AMMO = item("pistol_ammo", Item::new, new Item.Properties());
	public static final Item RIFLE_AMMO = item("rifle_ammo", Item::new, new Item.Properties());
	public static final Item AMMO_9MM = item("ammo_9mm", Item::new, new Item.Properties());
	public static final Item AMMO_44 = item("ammo_44", Item::new, new Item.Properties());
	public static final Item AMMO_12GA = item("ammo_12ga", Item::new, new Item.Properties());
	public static final Item AMMO_556 = item("ammo_556", Item::new, new Item.Properties());
	public static final Item AMMO_762 = item("ammo_762", Item::new, new Item.Properties());
	public static final Item AMMO_308 = item("ammo_308", Item::new, new Item.Properties());
	public static final Item AMMO_50 = item("ammo_50", Item::new, new Item.Properties());

	// State of Decay 2's iconic guns. Stats: magazine, damage, range, fire delay, reload ticks, noise radius, recoil,
	// spread, sound pitch[, pellets, automatic]. Their look comes from the local SoD2 Assets pack (tools/sod2_import.py).
	public static final Item PISTOL = gun("pistol", new GunItem.Stats(7, 7.0F, 48, 4, 30, 32, 3.0F, 1.2F, 1.5F), () -> PISTOL_AMMO);
	public static final Item GLOCK17 = gun("glock17", new GunItem.Stats(17, 5.0F, 48, 3, 28, 30, 2.0F, 1.4F, 1.7F), () -> AMMO_9MM);
	public static final Item M9 = gun("m9", new GunItem.Stats(15, 5.5F, 48, 3, 30, 30, 2.2F, 1.3F, 1.65F), () -> AMMO_9MM);
	public static final Item REVOLVER44 = gun("revolver44", new GunItem.Stats(6, 13.0F, 56, 10, 50, 44, 7.0F, 0.8F, 1.0F), () -> AMMO_44);
	public static final Item SHOTGUN870 = gun("shotgun870", new GunItem.Stats(6, 3.5F, 24, 18, 60, 48, 7.0F, 7.0F, 0.7F, 8, false), () -> AMMO_12GA);
	public static final Item AA12 = gun("aa12", new GunItem.Stats(8, 3.0F, 24, 6, 70, 52, 4.0F, 7.5F, 0.75F, 8, true), () -> AMMO_12GA);
	public static final Item AR15 = gun("ar15", new GunItem.Stats(30, 6.0F, 80, 3, 45, 48, 1.4F, 1.0F, 1.25F, 1, true), () -> AMMO_556);
	public static final Item AK47 = gun("ak47", new GunItem.Stats(30, 7.5F, 80, 3, 45, 52, 1.9F, 1.4F, 1.05F, 1, true), () -> AMMO_762);
	public static final Item SCARH = gun("scarh", new GunItem.Stats(20, 9.5F, 90, 3, 48, 56, 2.4F, 1.1F, 0.95F, 1, true), () -> AMMO_308);
	public static final Item M14 = gun("m14", new GunItem.Stats(20, 10.0F, 96, 5, 48, 56, 3.0F, 0.6F, 0.95F), () -> AMMO_308);
	public static final Item RIFLE = gun("rifle", new GunItem.Stats(5, 15.0F, 120, 20, 55, 60, 6.0F, 0.2F, 0.8F), () -> RIFLE_AMMO);
	public static final Item BOLT50 = gun("bolt50", new GunItem.Stats(5, 32.0F, 160, 30, 70, 90, 10.0F, 0.1F, 0.55F), () -> AMMO_50);
	public static final Item MP5 = gun("mp5", new GunItem.Stats(30, 4.5F, 56, 2, 40, 32, 1.0F, 1.6F, 1.6F, 1, true), () -> AMMO_9MM);
	public static final Item THOMPSON = gun("thompson", new GunItem.Stats(30, 6.0F, 56, 2, 50, 40, 1.4F, 1.8F, 1.3F, 1, true), () -> PISTOL_AMMO);

	public static final Holder<MobEffect> BLOOD_PLAGUE = Registry.registerForHolder(BuiltInRegistries.MOB_EFFECT, SodCraft.id("blood_plague"),
		new BloodPlague());
	public static final Item PLAGUE_SAMPLE = item("plague_sample", Item::new, new Item.Properties());
	public static final Item PLAGUE_CURE = item("plague_cure", PlagueCureItem::new, new Item.Properties().stacksTo(16));

	public static final EntityType<SodZombie> PLAGUE_ZOMBIE = zombie("plague_zombie", (t, l) -> new SodZombie(t, l, true));
	public static final EntityType<Feral> FERAL = zombie("feral", (t, l) -> new Feral(t, l, false));
	public static final EntityType<Feral> PLAGUE_FERAL = zombie("plague_feral", (t, l) -> new Feral(t, l, true));
	public static final EntityType<Bloater> BLOATER = zombie("bloater", Bloater::new);
	public static final EntityType<Juggernaut> JUGGERNAUT = zombie("juggernaut", (t, l) -> new Juggernaut(t, l, false));
	public static final EntityType<Juggernaut> PLAGUE_JUGGERNAUT = zombie("plague_juggernaut", (t, l) -> new Juggernaut(t, l, true));
	public static final EntityType<ArmoredZombie> ARMORED_ZOMBIE = zombie("armored_zombie", ArmoredZombie::new);

	private ModContent() {
	}

	/** Zombie-sized; bigger freaks grow through their SCALE attribute. */
	private static <T extends SodZombie> EntityType<T> zombie(final String name, final EntityType.EntityFactory<T> factory) {
		ResourceKey<EntityType<?>> key = ResourceKey.create(Registries.ENTITY_TYPE, SodCraft.id(name));
		return Registry.register(BuiltInRegistries.ENTITY_TYPE, key, EntityType.Builder.<T>of(factory, MobCategory.MONSTER)
			.sized(0.6F, 1.95F).eyeHeight(1.74F).clientTrackingRange(8).build(key));
	}

	private static Item gun(final String name, final GunItem.Stats stats, final java.util.function.Supplier<Item> ammo) {
		return item(name, p -> new GunItem(stats, ammo, p), new Item.Properties());
	}

	private static Item item(final String name, final java.util.function.Function<Item.Properties, Item> factory, final Item.Properties properties) {
		ResourceKey<Item> key = ResourceKey.create(Registries.ITEM, SodCraft.id(name));
		return Registry.register(BuiltInRegistries.ITEM, key, factory.apply(properties.setId(key)));
	}

	/** Loads this class, which registers everything above. */
	static void init() {
	}
}
