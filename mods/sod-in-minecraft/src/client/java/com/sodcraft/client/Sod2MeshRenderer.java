package com.sodcraft.client;

import com.mojang.blaze3d.vertex.PoseStack;
import com.mojang.blaze3d.vertex.VertexConsumer;
import com.mojang.serialization.Codec;
import com.mojang.serialization.MapCodec;
import com.mojang.serialization.codecs.RecordCodecBuilder;
import com.sodcraft.SodCraft;
import java.util.function.Consumer;
import net.minecraft.client.renderer.SubmitNodeCollector;
import net.minecraft.client.renderer.rendertype.RenderTypes;
import net.minecraft.client.renderer.special.NoDataSpecialModelRenderer;
import net.minecraft.client.renderer.special.SpecialModelRenderer;
import net.minecraft.resources.Identifier;
import org.joml.Vector3f;
import org.joml.Vector3fc;

/**
 * Draws a State of Decay 2 mesh (Sod2Mesh) with its own texture as an item: the "sodcraft:sod2_mesh" special model,
 * used by the item definitions in the local "SoD2 Assets" pack. Triangles go out as degenerate quads (entity render
 * types draw quads); lighting and overlay are Minecraft's own.
 */
public final class Sod2MeshRenderer implements NoDataSpecialModelRenderer {
	private final Sod2Mesh mesh;
	private final Identifier texture;

	private Sod2MeshRenderer(final Sod2Mesh mesh, final Identifier texture) {
		this.mesh = mesh;
		this.texture = texture;
	}

	@Override
	public void submit(final PoseStack poseStack, final SubmitNodeCollector collector, final int light, final int overlay, final boolean foil, final int outline) {
		if (mesh == null) {
			return;
		}

		collector.submitCustomGeometry(poseStack, RenderTypes.entityCutout(texture), (pose, out) -> emit(pose, out, light, overlay));
	}

	private void emit(final PoseStack.Pose pose, final VertexConsumer out, final int light, final int overlay) {
		float[] v = mesh.vertices();
		int[] idx = mesh.indices();
		for (int t = 0; t + 2 < idx.length; t += 3) {
			vertex(pose, out, v, idx[t], light, overlay);
			vertex(pose, out, v, idx[t + 1], light, overlay);
			vertex(pose, out, v, idx[t + 2], light, overlay);
			vertex(pose, out, v, idx[t + 2], light, overlay);
		}
	}

	private static void vertex(final PoseStack.Pose pose, final VertexConsumer out, final float[] v, final int i, final int light, final int overlay) {
		int o = i * Sod2Mesh.STRIDE;
		out.addVertex(pose, v[o], v[o + 1], v[o + 2])
			.setColor(-1)
			.setUv(v[o + 6], v[o + 7])
			.setOverlay(overlay)
			.setLight(light)
			.setNormal(pose, v[o + 3], v[o + 4], v[o + 5]);
	}

	@Override
	public void getExtents(final Consumer<Vector3fc> out) {
		if (mesh == null) {
			return;
		}

		float[] a = mesh.min(), b = mesh.max();
		for (int k = 0; k < 8; k++) {
			out.accept(new Vector3f((k & 1) == 0 ? a[0] : b[0], (k & 2) == 0 ? a[1] : b[1], (k & 4) == 0 ? a[2] : b[2]));
		}
	}

	/** {"type": "sodcraft:sod2_mesh", "mesh": "<name>"}: the mesh and texture named <name> in the SoD2 Assets pack. */
	public record Unbaked(String mesh) implements SpecialModelRenderer.Unbaked {
		public static final MapCodec<Unbaked> CODEC = RecordCodecBuilder.mapCodec(i -> i.group(
			Codec.STRING.fieldOf("mesh").forGetter(Unbaked::mesh)).apply(i, Unbaked::new));

		@Override
		public SpecialModelRenderer<?> bake(final SpecialModelRenderer.BakingContext context) {
			return new Sod2MeshRenderer(Sod2Mesh.load(mesh).orElse(null), SodCraft.id("textures/sod2/" + mesh + ".png"));
		}

		@Override
		public MapCodec<Unbaked> type() {
			return CODEC;
		}
	}
}
