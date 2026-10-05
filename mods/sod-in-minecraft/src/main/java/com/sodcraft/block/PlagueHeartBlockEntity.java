package com.sodcraft.block;

import com.sodcraft.ModContent;
import com.sodcraft.SodCraft;
import java.util.List;
import net.minecraft.core.BlockPos;
import net.minecraft.core.particles.ParticleTypes;
import net.minecraft.network.chat.Component;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;
import net.minecraft.util.RandomSource;
import net.minecraft.world.entity.EntitySpawnReason;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.EntityTypes;
import net.minecraft.world.entity.Mob;
import net.minecraft.world.entity.monster.zombie.Zombie;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.entity.BlockEntity;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.storage.ValueInput;
import net.minecraft.world.level.storage.ValueOutput;
import net.minecraft.world.phys.AABB;

/**
 * The Plague Heart's brain. Once a second (server only): if it's dark and a player is within ACTIVE_RANGE, a wave
 * comes every WAVE_INTERVAL ticks, the first one straight away. Waves grow with every wave sent (the longer you leave
 * it, the stronger it gets); every other wave brings a Screamer. Hitting the heart spawns defenders, day or night.
 */
public class PlagueHeartBlockEntity extends BlockEntity {
	/** Zombies it spawned carry this tag (to count them). */
	public static final String HEART_TAG = "sodcraft_heart";
	private static final double ACTIVE_RANGE = 48.0;
	private static final int WAVE_INTERVAL = 600; // 30 s
	private static final int DEFEND_INTERVAL = 300; // 15 s
	private static final int MAX_ALIVE = 16;

	private int age;
	private int waves;
	private int waveCooldown;
	private int defendCooldown;

	public PlagueHeartBlockEntity(final BlockPos pos, final BlockState state) {
		super(ModContent.PLAGUE_HEART_BE, pos, state);
	}

	public static void serverTick(final Level level, final BlockPos pos, final BlockState state, final PlagueHeartBlockEntity heart) {
		if (!(level instanceof ServerLevel serverLevel) || ++heart.age % 20 != 0) {
			return;
		}

		double cx = pos.getX() + 0.5, cy = pos.getY() + 0.5, cz = pos.getZ() + 0.5;
		serverLevel.sendParticles(ParticleTypes.CRIMSON_SPORE, cx, cy, cz, 6, 0.6, 0.6, 0.6, 0.0);
		heart.defendCooldown = Math.max(0, heart.defendCooldown - 20);
		heart.waveCooldown = Math.max(0, heart.waveCooldown - 20);

		Player player = serverLevel.getNearestPlayer(cx, cy, cz, ACTIVE_RANGE, false);
		if (heart.age % 600 == 0) {
			SodCraft.LOG.info("plague heart at {}: player near: {}, dark outside: {}, next wave in {} s", pos.toShortString(), player != null,
				serverLevel.isDarkOutside(), heart.waveCooldown / 20);
		}

		if (player == null || !serverLevel.isDarkOutside() || heart.waveCooldown > 0) {
			return;
		}

		heart.waveCooldown = WAVE_INTERVAL;
		int alive = serverLevel.getEntitiesOfClass(Zombie.class, new AABB(pos).inflate(ACTIVE_RANGE), z -> z.entityTags().contains(HEART_TAG)).size();
		int size = Math.min(Math.min(3 + heart.waves, 8), MAX_ALIVE - alive);
		if (size <= 0) {
			return; // its horde is still out there
		}

		int spawned = heart.spawnAround(serverLevel, EntityTypes.ZOMBIE, size, 6, 14, player);
		if (heart.waves % 2 == 1) {
			spawned += heart.spawnAround(serverLevel, ModContent.SCREAMER, 1, 8, 14, player);
		}

		heart.waves++;
		heart.setChanged();
		serverLevel.playSound(null, cx, cy, cz, SoundEvents.WARDEN_HEARTBEAT, SoundSource.HOSTILE, 4.0F, 0.7F);
		tell(serverLevel, pos, Component.translatable("message.sodcraft.wave", heart.waves));
		SodCraft.LOG.info("plague heart at {}: wave {}, {} spawned ({} of its zombies already alive)", pos.toShortString(), heart.waves, spawned, alive);
	}

	/** A player hit the heart: defenders burst out next to it. */
	void defend(final ServerLevel level, final Player attacker) {
		if (defendCooldown > 0) {
			return;
		}

		defendCooldown = DEFEND_INTERVAL;
		int spawned = spawnAround(level, EntityTypes.ZOMBIE, 2 + Math.min(waves / 2, 3), 2, 5, attacker);
		BlockPos pos = getBlockPos();
		level.playSound(null, pos.getX() + 0.5, pos.getY() + 0.5, pos.getZ() + 0.5, SoundEvents.CREAKING_HEART_HURT, SoundSource.HOSTILE, 3.0F, 0.6F);
		tell(level, pos, Component.translatable("message.sodcraft.defend"));
		SodCraft.LOG.info("plague heart at {} defends: {} spawned", pos.toShortString(), spawned);
	}

	/** Spawn up to `count` mobs on free ground `minR`..`maxR` blocks around the heart, hunting `target`. */
	private <T extends Mob> int spawnAround(final ServerLevel level, final EntityType<T> type, final int count, final int minR, final int maxR, final Player target) {
		RandomSource random = level.getRandom();
		BlockPos center = getBlockPos();
		int spawned = 0;
		for (int i = 0; i < count * 6 && spawned < count; i++) {
			double angle = random.nextDouble() * Math.PI * 2.0;
			double r = minR + random.nextDouble() * (maxR - minR);
			BlockPos ground = groundAt(level, center.getX() + (int) Math.round(Math.cos(angle) * r), center.getY(), center.getZ() + (int) Math.round(Math.sin(angle) * r));
			if (ground == null) {
				continue;
			}

			T mob = type.spawn(level, ground, EntitySpawnReason.EVENT);
			if (mob == null) {
				continue;
			}

			mob.addTag(HEART_TAG);
			if (target != null && !target.isCreative() && !target.isSpectator()) {
				mob.setTarget(target);
			}

			level.sendParticles(ParticleTypes.LARGE_SMOKE, mob.getX(), mob.getY() + 0.5, mob.getZ(), 8, 0.3, 0.5, 0.3, 0.01);
			spawned++;
		}

		return spawned;
	}

	/** The free two-block space on solid ground near height y in column (x, z), or null. */
	private static BlockPos groundAt(final ServerLevel level, final int x, final int y, final int z) {
		BlockPos.MutableBlockPos p = new BlockPos.MutableBlockPos();
		for (int dy = 6; dy >= -8; dy--) {
			p.set(x, y + dy, z);
			if (level.getBlockState(p).isSolid() && level.getBlockState(p.above()).isAir() && level.getBlockState(p.above(2)).isAir()) {
				return p.above().immutable();
			}
		}

		return null;
	}

	private static void tell(final ServerLevel level, final BlockPos pos, final Component message) {
		List<Player> near = level.getEntitiesOfClass(Player.class, new AABB(pos).inflate(ACTIVE_RANGE));
		for (Player p : near) {
			p.sendOverlayMessage(message);
		}
	}

	/** The block is going away (mined, blown up, replaced). */
	@Override
	public void preRemoveSideEffects(final BlockPos pos, final BlockState state) {
		super.preRemoveSideEffects(pos, state);
		if (level instanceof ServerLevel serverLevel) {
			double cx = pos.getX() + 0.5, cy = pos.getY() + 0.5, cz = pos.getZ() + 0.5;
			serverLevel.sendParticles(ParticleTypes.LARGE_SMOKE, cx, cy, cz, 40, 0.5, 0.5, 0.5, 0.05);
			serverLevel.sendParticles(ParticleTypes.CRIMSON_SPORE, cx, cy, cz, 60, 1.0, 1.0, 1.0, 0.1);
			serverLevel.playSound(null, cx, cy, cz, SoundEvents.CREAKING_HEART_BREAK, SoundSource.BLOCKS, 3.0F, 0.5F);
			tell(serverLevel, pos, Component.translatable("message.sodcraft.heart_destroyed"));
			SodCraft.LOG.info("plague heart at {} destroyed after {} waves", pos.toShortString(), waves);
		}
	}

	@Override
	protected void saveAdditional(final ValueOutput output) {
		super.saveAdditional(output);
		output.putInt("waves", waves);
		output.putInt("wave_cooldown", waveCooldown);
	}

	@Override
	protected void loadAdditional(final ValueInput input) {
		super.loadAdditional(input);
		waves = input.getIntOr("waves", 0);
		waveCooldown = input.getIntOr("wave_cooldown", 0);
	}
}
