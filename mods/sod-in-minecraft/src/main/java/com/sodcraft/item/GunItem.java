package com.sodcraft.item;

import com.sodcraft.SodCraft;
import com.sodcraft.entity.ArmoredZombie;
import java.util.function.Supplier;
import net.minecraft.core.particles.ParticleTypes;
import net.minecraft.network.chat.Component;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;
import net.minecraft.util.RandomSource;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.InteractionResult;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.monster.zombie.Zombie;
import net.minecraft.world.entity.monster.zombie.ZombifiedPiglin;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.entity.projectile.ProjectileUtil;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.ItemUseAnimation;
import net.minecraft.world.level.ClipContext;
import net.minecraft.world.level.Level;
import net.minecraft.world.phys.BlockHitResult;
import net.minecraft.world.phys.EntityHitResult;
import net.minecraft.world.phys.HitResult;
import net.minecraft.world.phys.Vec3;

/**
 * A hitscan gun in the spirit of State of Decay 2. Right-click fires; crouch + right-click (or firing on empty)
 * reloads from ammo in the inventory. The magazine is the item's durability bar (shots fired = damage). Every shot is
 * loud: zombies within {@link Stats#noise} blocks come for the shooter. Headshots deal {@link #HEADSHOT} times damage.
 */
public class GunItem extends Item {
	private static final double HEADSHOT = 2.5;

	/** Tuning for one gun. Ticks are 1/20 s; recoil and spread in degrees. */
	public record Stats(int magazine, float damage, double range, int fireDelay, int reloadTicks, double noise, float recoil, float spread,
		float pitch, int pellets, boolean auto) {
		/** A single-shot (semi-automatic) gun. */
		public Stats(final int magazine, final float damage, final double range, final int fireDelay, final int reloadTicks, final double noise,
			final float recoil, final float spread, final float pitch) {
			this(magazine, damage, range, fireDelay, reloadTicks, noise, recoil, spread, pitch, 1, false);
		}
	}

	private final Stats stats;
	private final Supplier<Item> ammo;

	public GunItem(final Stats stats, final Supplier<Item> ammo, final Properties properties) {
		super(properties.durability(stats.magazine()));
		this.stats = stats;
		this.ammo = ammo;
	}

	public static int loaded(final ItemStack gun) {
		return gun.getMaxDamage() - gun.getDamageValue();
	}

	@Override
	public InteractionResult use(final Level level, final Player player, final InteractionHand hand) {
		ItemStack gun = player.getItemInHand(hand);
		if (player.getCooldowns().isOnCooldown(gun)) {
			return InteractionResult.FAIL;
		}

		if (player.isShiftKeyDown() || loaded(gun) <= 0) {
			if (level instanceof ServerLevel serverLevel) {
				reload(serverLevel, player, gun);
			}

			return InteractionResult.CONSUME;
		}

		shoot(level, player, gun);
		if (stats.auto()) {
			player.startUsingItem(hand); // keeps firing while the button is held: onUseTick
		}

		return InteractionResult.CONSUME;
	}

	private void shoot(final Level level, final Player player, final ItemStack gun) {
		if (level instanceof ServerLevel serverLevel) {
			fire(serverLevel, player, gun);
		} else {
			// the camera kicks up (client side: the local player's view)
			RandomSource random = player.getRandom();
			player.setXRot(player.getXRot() - stats.recoil());
			player.setYRot(player.getYRot() + (random.nextFloat() - 0.5F) * stats.recoil() * 0.6F);
		}
	}

	@Override
	public void onUseTick(final Level level, final LivingEntity user, final ItemStack gun, final int remaining) {
		if (!(user instanceof Player player) || player.getCooldowns().isOnCooldown(gun)) {
			return;
		}

		if (loaded(gun) <= 0) {
			player.stopUsingItem();
			if (level instanceof ServerLevel serverLevel) {
				reload(serverLevel, player, gun);
			}

			return;
		}

		shoot(level, player, gun);
	}

	@Override
	public int getUseDuration(final ItemStack gun, final LivingEntity user) {
		return stats.auto() ? 72000 : 0;
	}

	@Override
	public ItemUseAnimation getUseAnimation(final ItemStack gun) {
		return ItemUseAnimation.NONE;
	}

	private void fire(final ServerLevel level, final Player player, final ItemStack gun) {
		Vec3 eye = player.getEyePosition();
		Vec3 look = player.getViewVector(1.0F);
		boolean headshotSeen = false, armoredSeen = false;
		for (int p = 0; p < stats.pellets(); p++) {
			int result = pellet(level, player, eye, look);
			headshotSeen |= result == 2;
			armoredSeen |= result == 3;
		}

		level.sendParticles(ParticleTypes.SMOKE, eye.x + look.x * 0.9, eye.y + look.y * 0.9 - 0.15, eye.z + look.z * 0.9, 3, 0.03, 0.03, 0.03, 0.01);
		level.playSound(null, player.getX(), player.getY(), player.getZ(), SoundEvents.FIREWORK_ROCKET_BLAST, SoundSource.PLAYERS, 3.0F, stats.pitch());
		if (headshotSeen) {
			player.sendOverlayMessage(Component.translatable("message.sodcraft.headshot"));
		} else if (armoredSeen) {
			player.sendOverlayMessage(Component.translatable("message.sodcraft.armored"));
		}

		alertHorde(level, player);
		if (!player.getAbilities().instabuild) {
			gun.setDamageValue(gun.getDamageValue() + 1);
		}

		player.getCooldowns().addCooldown(gun, stats.fireDelay());
	}

	/** One bullet or pellet. 0 = nothing alive hit, 1 = hit, 2 = headshot, 3 = headshot stopped by a helmet. */
	private int pellet(final ServerLevel level, final Player player, final Vec3 eye, final Vec3 look) {
		RandomSource random = player.getRandom();
		double s = Math.toRadians(stats.spread());
		Vec3 dir = look.add((random.nextDouble() - 0.5) * s, (random.nextDouble() - 0.5) * s, (random.nextDouble() - 0.5) * s).normalize();
		Vec3 end = eye.add(dir.scale(stats.range()));
		BlockHitResult block = level.clip(new ClipContext(eye, end, ClipContext.Block.COLLIDER, ClipContext.Fluid.NONE, player));
		if (block.getType() != HitResult.Type.MISS) {
			end = block.getLocation();
		}

		EntityHitResult hit = ProjectileUtil.getEntityHitResult(level, player, eye, end, player.getBoundingBox().expandTowards(dir.scale(stats.range())).inflate(1.0),
			e -> e instanceof LivingEntity && e.isAlive() && !e.isSpectator() && e.isPickable() && e != player, 0.3F);
		Vec3 impact = hit != null ? hit.getLocation() : end;
		tracer(level, eye.add(dir.scale(1.2)), impact);
		if (hit != null && hit.getEntity() instanceof LivingEntity target) {
			boolean headshot = impact.y >= target.getEyeY() - 0.3;
			boolean helmet = headshot && target instanceof ArmoredZombie; // the riot helmet takes it
			target.damageCooldownTime = 0; // fast fire and pellets land inside the usual hurt cooldown
			target.hurtServer(level, level.damageSources().playerAttack(player), headshot && !helmet ? (float) (stats.damage() * HEADSHOT) : stats.damage());
			level.sendParticles(ParticleTypes.CRIT, impact.x, impact.y, impact.z, headshot ? 10 : 4, 0.1, 0.1, 0.1, 0.2);
			return helmet ? 3 : headshot ? 2 : 1;
		}

		if (block.getType() != HitResult.Type.MISS) {
			level.sendParticles(ParticleTypes.POOF, impact.x, impact.y, impact.z, 2, 0.05, 0.05, 0.05, 0.01);
		}

		return 0;
	}

	private static void tracer(final ServerLevel level, final Vec3 from, final Vec3 to) {
		Vec3 step = to.subtract(from);
		int n = (int) Math.min(40, step.length() / 1.5);
		for (int i = 0; i < n; i++) {
			Vec3 p = from.add(step.scale(i / (double) n));
			level.sendParticles(ParticleTypes.ELECTRIC_SPARK, p.x, p.y, p.z, 1, 0.0, 0.0, 0.0, 0.0);
		}
	}

	/** Gunfire is loud: every zombie in earshot comes. */
	private void alertHorde(final ServerLevel level, final Player player) {
		if (player.isCreative() || player.isSpectator()) {
			return;
		}

		for (Zombie z : level.getEntitiesOfClass(Zombie.class, player.getBoundingBox().inflate(stats.noise()), z -> z.isAlive() && !(z instanceof ZombifiedPiglin))) {
			if (z.getTarget() != player) {
				z.setTarget(player);
			}
		}
	}

	private void reload(final ServerLevel level, final Player player, final ItemStack gun) {
		int need = gun.getDamageValue();
		if (need <= 0) {
			return;
		}

		int taken = player.getAbilities().instabuild ? need : takeAmmo(player, need);
		if (taken <= 0) {
			level.playSound(null, player.getX(), player.getY(), player.getZ(), SoundEvents.DISPENSER_FAIL, SoundSource.PLAYERS, 1.0F, 1.6F);
			player.sendOverlayMessage(Component.translatable("message.sodcraft.no_ammo", Component.translatable(ammo.get().getDescriptionId())));
			player.getCooldowns().addCooldown(gun, 10);
			return;
		}

		gun.setDamageValue(need - taken);
		level.playSound(null, player.getX(), player.getY(), player.getZ(), SoundEvents.CROSSBOW_LOADING_END, SoundSource.PLAYERS, 1.0F, 1.2F);
		player.sendOverlayMessage(Component.translatable("message.sodcraft.reloaded", loaded(gun), gun.getMaxDamage()));
		player.getCooldowns().addCooldown(gun, stats.reloadTicks());
		SodCraft.LOG.debug("reloaded {} rounds", taken);
	}

	private int takeAmmo(final Player player, final int need) {
		int taken = 0;
		for (ItemStack stack : player.getInventory().getNonEquipmentItems()) {
			if (taken >= need) {
				break;
			}

			if (!stack.isEmpty() && stack.getItem() == ammo.get()) {
				int n = Math.min(need - taken, stack.getCount());
				stack.shrink(n);
				taken += n;
			}
		}

		return taken;
	}
}
