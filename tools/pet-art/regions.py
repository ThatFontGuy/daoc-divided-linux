"""Classify each texel into body regions from its 3D position (T-pose, z up, -y front)."""
import numpy as np
from PIL import Image

COLORS = {
    "empty": (20, 20, 20), "head": (255, 205, 0), "neck": (255, 80, 200), "chest": (220, 40, 40),
    "back": (140, 20, 20), "belly": (255, 120, 60), "hips": (200, 90, 255), "upperarm": (0, 160, 255),
    "forearm": (0, 90, 200), "hand": (0, 230, 230), "thigh": (60, 200, 60), "shin": (20, 120, 20),
    "foot": (230, 230, 230),
}


def landmarks(tm):
    """Derive body landmarks from the covered surface points."""
    p = tm.pos[tm.covered]
    x, y, z = p[:, 0], p[:, 1], p[:, 2]
    height = z.max()
    reach = np.abs(x).max()
    core = np.abs(x) < 6
    # Shoulder height: where the widest arm points live.
    arm = np.abs(x) > reach * 0.45
    shoulder_z = np.median(z[arm]) if arm.any() else height * 0.8
    return dict(height=height, reach=reach, shoulder_z=shoulder_z,
                neck_z=shoulder_z + 0.06 * height, chin_z=shoulder_z + 0.12 * height,
                waist_z=0.58 * height, hip_z=0.47 * height, knee_z=0.27 * height, ankle_z=0.06 * height,
                shoulder_x=reach * 0.30, elbow_x=reach * 0.58, wrist_x=reach * 0.82)


def classify(tm, L=None):
    L = L or landmarks(tm)
    x, y, z = tm.pos[..., 0], tm.pos[..., 1], tm.pos[..., 2]
    ax = np.abs(x)
    region = np.full(tm.covered.shape, "empty", dtype=object)
    armzone = (ax > L["shoulder_x"]) & (z > L["shoulder_z"] - 0.10 * L["height"])
    region[:] = "empty"
    c = tm.covered
    region[c & (z >= L["chin_z"])] = "head"
    region[c & (z >= L["neck_z"]) & (z < L["chin_z"]) & ~armzone] = "neck"
    torso = c & ~armzone & (z < L["neck_z"]) & (z >= L["hip_z"])
    region[torso & (z >= L["waist_z"]) & (y < 0)] = "chest"
    region[torso & (z >= L["waist_z"]) & (y >= 0)] = "back"
    region[torso & (z < L["waist_z"])] = "belly"
    region[c & ~armzone & (z < L["hip_z"]) & (z >= L["hip_z"] - 0.06 * L["height"])] = "hips"
    legs = c & ~armzone & (z < L["hip_z"] - 0.06 * L["height"])
    region[legs & (z >= L["knee_z"])] = "thigh"
    region[legs & (z < L["knee_z"]) & (z >= L["ankle_z"])] = "shin"
    region[legs & (z < L["ankle_z"])] = "foot"
    region[c & armzone & (ax < L["elbow_x"])] = "upperarm"
    region[c & armzone & (ax >= L["elbow_x"]) & (ax < L["wrist_x"])] = "forearm"
    region[c & armzone & (ax >= L["wrist_x"])] = "hand"
    return region, L


def region_image(region):
    img = np.zeros(region.shape + (3,), np.uint8)
    for name, col in COLORS.items():
        img[region == name] = col
    return Image.fromarray(img)
