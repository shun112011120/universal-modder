package com.sodcraft.client;

import com.sodcraft.SodCraft;
import java.io.IOException;
import java.io.InputStream;
import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.util.Optional;
import net.minecraft.client.Minecraft;
import net.minecraft.resources.Identifier;
import net.minecraft.server.packs.resources.Resource;

/**
 * A mesh written by tools/sod2_import.py from the owner's State of Decay 2 install, read from the local "SoD2 Assets"
 * resource pack (assets/sodcraft/sod2/<name>.mesh). Format: "SODM", int version, int vertices, int indices,
 * then 8 floats per vertex (x y z nx ny nz u v) and int triangle indices, little-endian, in item space.
 */
public record Sod2Mesh(float[] vertices, int[] indices, float[] min, float[] max) {
	static final int STRIDE = 8;

	public static Optional<Sod2Mesh> load(final String name) {
		Identifier id = SodCraft.id("sod2/" + name + ".mesh");
		Optional<Resource> resource = Minecraft.getInstance().getResourceManager().getResource(id);
		if (resource.isEmpty()) {
			return Optional.empty();
		}

		try (InputStream in = resource.get().open()) {
			ByteBuffer b = ByteBuffer.wrap(in.readAllBytes()).order(ByteOrder.LITTLE_ENDIAN);
			if (b.getInt() != 0x4D444F53 || b.getInt() != 1) { // "SODM" read little-endian, version 1
				SodCraft.LOG.warn("{}: not a SoDcraft mesh", id);
				return Optional.empty();
			}

			int nv = b.getInt(), ni = b.getInt();
			float[] v = new float[nv * STRIDE];
			b.asFloatBuffer().get(v);
			b.position(b.position() + v.length * 4);
			int[] idx = new int[ni];
			b.asIntBuffer().get(idx);
			float[] min = {Float.MAX_VALUE, Float.MAX_VALUE, Float.MAX_VALUE}, max = {-Float.MAX_VALUE, -Float.MAX_VALUE, -Float.MAX_VALUE};
			for (int i = 0; i < nv; i++) {
				for (int k = 0; k < 3; k++) {
					min[k] = Math.min(min[k], v[i * STRIDE + k]);
					max[k] = Math.max(max[k], v[i * STRIDE + k]);
				}
			}

			SodCraft.LOG.info("SoD2 mesh {}: {} vertices, {} triangles", name, nv, ni / 3);
			return Optional.of(new Sod2Mesh(v, idx, min, max));
		} catch (IOException | RuntimeException e) {
			SodCraft.LOG.warn("couldn't read SoD2 mesh {}: {}", id, e.toString());
			return Optional.empty();
		}
	}
}
