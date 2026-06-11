"""
Промпты GIGAvibe. Активный набор — танец на фестивале (5 с, cinematic handheld).
Переопределение: LTX_PROMPT / LTX_NEGATIVE_PROMPT в .env
"""

# Танец + фестиваль (img2vid LTX). ВАЖНО для LTX: промпт описывает ДВИЖЕНИЕ и камеру во времени,
# а НЕ пересказывает статичную сцену и без мета-инструкций («use the image»). Длина < 128 токенов,
# иначе хвост (как раз про движение) обрезается. Огни «продолжают мигать всё время» — удерживает фон.
# Подобрано экспериментально (рецепт P: guidance 3.5 / guidance_rescale 0.4 / 121 кадр).
FESTIVAL_PROMPT = (
    "A young woman at a vibrant music festival smiles and gently sways to the music, her hair "
    "moving softly, staying centered and in sharp focus. Behind her, bright multicolored stage "
    "lights keep flashing, sweeping and twinkling the entire time, the lively festival glow stays "
    "vivid and colorful. The camera is steady with a subtle handheld sway."
)

NEGATIVE_PROMPT = (
    "sepia, faded background, dull colors, plain background, lights turning off, "
    "out of focus, defocused, subject dissolving, fading away, bokeh blur over face, "
    "static, frozen frame, no motion, morphing face, identity change, distorted face, "
    "deformed hands, overexposed, washed out, low quality, watermark, text"
)

# Предыдущий фестивальный стиль (ТЗ PDF + compose_festival_still)
FESTIVAL_PROMPT_TZ = (
    "Dynamic summer music festival scene, the same person from the reference photo remains "
    "the main subject with stable face, outdoor concert with moving crowd silhouettes, "
    "colorful balloons floating and drifting in the air, lime green and hot pink stage "
    "lights pulsing and sweeping, cyan laser haze, golden hour glow, confetti falling, "
    "background bokeh lights twinkling, glossy 3D festive shapes, visible camera motion, "
    "energetic party atmosphere, animate summer memories, cinematic, smooth temporal "
    "motion, high quality"
)

NEGATIVE_PROMPT_TZ = (
    "worst quality, low resolution, blurry, static photograph, frozen video, no movement, "
    "still background, single frame repeated, jittery, morphing face, identity change, "
    "distorted face, extra limbs, indoor, office, winter, snow, plain background, "
    "watermark, text, logo, subtitle, horror, dark"
)

# Ключевой кадр InstantID (генерация СТАТИЧНОГО фото, не видео):
# фотореалистичный гость на фестивале с сохранением лица.
KEYFRAME_FESTIVAL_PROMPT = (
    "photorealistic portrait of the same person at a vibrant summer music festival, "
    "standing in front of a concert stage with bright colorful spotlights, lively crowd "
    "and bokeh lights in the background, confetti in the air, warm golden hour evening "
    "light, joyful festive mood, cinematic depth of field, ultra detailed, high quality, "
    "natural skin texture, sharp focus on face"
)

KEYFRAME_NEGATIVE_PROMPT = (
    "cartoon, anime, illustration, painting, 3d render, cgi, plastic skin, deformed face, "
    "distorted features, extra fingers, bad anatomy, blurry, low quality, watermark, text, "
    "logo, duplicate person, disfigured, identity change, indoor office, plain background"
)

# Бренд-стиль «glossy 3D + living portrait» по Seedance-референсу IMG_9240:
# реалистичное лицо гостя на фоне глянцевых 3D-объектов (надувной цветок, клевер,
# шары, шахматная лента), градиент изумруд→бирюза, частицы света.
# Лицо/кожа остаются фотореалистичными (InstantID), стилизуется фон и объекты.
KEYFRAME_BRAND_PROMPT = (
    "photorealistic same person, joyful smile, white t-shirt, sharp natural face, "
    "glossy 3D brand commercial, emerald turquoise gradient, pink inflatable flower, "
    "lime clover shapes, floating balloons, black white checkered ribbon, sparkles, "
    "soft daylight, saturated summer festival, living portrait, vertical 9:16"
)

KEYFRAME_BRAND_NEGATIVE_PROMPT = (
    "cartoon face, anime, cgi face, plastic skin, deformed face, distorted features, "
    "blurry face, low quality, watermark, text, logo, duplicate person, identity change, "
    "dark, dull colors, cluttered background"
)

# LTX-промпт под уже сгенерированный brand keyframe: не пересоздаём сцену, а оживляем её.
# ВАЖНО для LTX i2v: при keyframe модель склонна «примораживать» сцену → нужно ЯВНО и
# настойчиво описывать непрерывное движение во времени (continuously / the whole time),
# иначе получается почти статичный клип. Лицо держим стабильным, двигаем камеру и объекты.
LTX_BRAND_PROMPT = (
    "A glossy 3D brand living portrait of the same smiling person. The camera continuously "
    "pushes in toward her face with a smooth dolly motion the entire time. Her hair sways and "
    "flutters, she blinks and her smile shifts naturally. Around her, pink flowers, lime green "
    "clovers, glossy balloons and a black-white checkered ribbon keep floating, drifting and "
    "rotating through the air nonstop. The emerald-to-turquoise background shimmers and sparkles "
    "continuously. Lively, energetic summer commercial, constant fluid motion, dynamic scene."
)

LTX_BRAND_NEGATIVE_PROMPT = (
    "static, frozen frame, still image, no motion, motionless, stilted, looping freeze, "
    "cartoon face, anime face, identity change, face morphing, distorted face, melting skin, "
    "extra person, duplicate face, blurry face, overexposed face, dull colors, text, watermark, "
    "aggressive camera shake, warping background"
)

# --- Festival portrait (InstantID, один финальный кадр 7–10s из Seedance/nana-banana брифа) ---

FESTIVAL_PORTRAIT_SCENE = (
    "bright playful scene with glossy 3D inflatable-style objects, a large pink flower, "
    "lime-green clover flowers, floating balloons, a black-and-white checkered ribbon, "
    "a soft green glowing brand mark, smooth gradient from emerald green to turquoise blue, "
    "subtle sparkles and floating light particles, decorative atmospheric festival frame "
    "assembled around the portrait, confetti sparks in the air"
)

FESTIVAL_PORTRAIT_NEGATIVE = (
    "cartoon face, anime face, cgi face, plastic skin, deformed face, distorted features, "
    "extra fingers, bad anatomy, blurry face, out of focus face, low quality, watermark, "
    "text, logo, subtitle, duplicate person, identity change, dark, dull colors, muddy colors, "
    "plain background, indoor office, winter, horror, aggressive motion blur, cropped face"
)


def _age_phrase(profile: "GuestProfile | None") -> str:
    if profile is None or profile.age_years is None:
        return "in their twenties"
    years = profile.age_years
    if profile.age_group == "child":
        return f"{years} years old"
    if profile.age_group == "senior":
        if years >= 70:
            return f"about {years} years old"
        return f"in their {max(50, (years // 10) * 10)}s"
    if years < 23:
        return "early twenties"
    if years < 30:
        return "mid twenties"
    if years < 40:
        return "late twenties"
    if years < 55:
        return "forties"
    return f"about {years} years old"


def _subject_clause(profile: "GuestProfile | None") -> str:
    """Subject line adapted from guest profile (gender, age, build)."""
    age = _age_phrase(profile)
    build = profile.build if profile else "medium"
    shirt = {
        "slim": "fitted white t-shirt",
        "medium": "white t-shirt",
        "full": "comfortable white t-shirt",
    }[build]

    if profile is None:
        return (
            f"a young person ({age}), {shirt}, warm natural hair, "
            "genuine joyful smile with a playful wink, looking at the camera"
        )

    if profile.gender == "male":
        if profile.age_group == "child":
            noun = f"a cheerful boy ({age})"
            hair = "natural hair"
        elif profile.age_group == "senior":
            noun = f"a cheerful man ({age})"
            hair = "natural hair"
        else:
            noun = f"a young man ({age})"
            hair = "natural hair"
    else:
        if profile.age_group == "child":
            noun = f"a cheerful girl ({age})"
            hair = "natural hair"
        elif profile.age_group == "senior":
            noun = f"a cheerful woman ({age})"
            hair = "natural hair"
        else:
            noun = f"a young woman ({age})"
            hair = "warm brown wavy hair"

    return (
        f"{noun}, {shirt}, {hair}, genuine joyful smile with a playful wink, "
        "looking at the camera, photorealistic living portrait"
    )


# Festival toon (PuLID-FLUX): Pixar/Disney 3D + brand-сцена, короткий промпт (T5 ≤128).
FESTIVAL_TOON_SCENE = (
    "Disney Pixar 3D animated character, full body, glossy subsurface skin, soft cartoon proportions, "
    "joyful smile, standing in a bright festival brand scene, emerald to turquoise gradient, "
    "pink inflatable flowers, lime clover shapes, floating balloons, confetti sparks, "
    "even soft light, vertical 9:16 portrait"
)

FESTIVAL_TOON_NEGATIVE = (
    "photorealistic, raw photo, realistic skin pores, deformed, extra limbs, bad anatomy, "
    "blurry, watermark, text, logo, duplicate person, dark, horror, uncanny"
)


def build_festival_toon_prompt(profile: "GuestProfile | None") -> tuple[str, str]:
    """PuLID-FLUX: stylized Disney 3D + brand scene; identity — из ref-фото (лицо)."""
    base = "same person as reference, " + FESTIVAL_TOON_SCENE
    if profile is None:
        return base, FESTIVAL_TOON_NEGATIVE
    # Без «young man / natural hair» — PuLID держит лицо, тело рисуем в cartoon-стylize.
    return base, FESTIVAL_TOON_NEGATIVE


def _nanobanana_group_size(n: int) -> str:
    if n == 2:
        return "two people"
    if n == 3:
        return "three people"
    if n == 4:
        return "four people"
    return f"{n} people"


def _nanobanana_subject(profile: "GuestProfile | None") -> str:
    if profile is None:
        return "the same person as in the reference photo (same face identity and likeness)"
    if profile.is_group():
        who = _nanobanana_group_size(profile.face_count)
        return (
            f"{who} from the reference photo — keep every visible person, "
            "each with the same recognizable face, hairstyle and likeness"
        )
    age = _age_phrase(profile)
    if profile.gender == "male":
        who = f"a boy ({age})" if profile.age_group == "child" else f"a man ({age})"
    elif profile.gender == "female":
        who = f"a girl ({age})" if profile.age_group == "child" else f"a woman ({age})"
    else:
        who = f"a person ({age})"
    return f"{who}, same person as the reference photo, same face identity and likeness"


def _nanobanana_profile_identity_notes(profile: "GuestProfile | None") -> str:
    """Дополнения к блоку identity под возраст и комплекцию гостя."""
    if profile is None or profile.is_group():
        return ""
    notes: list[str] = []
    if profile.age_group == "child":
        notes.append("preserve child proportions and age-appropriate youthful features")
    elif profile.age_group == "senior":
        notes.append(
            "preserve natural mature age-appropriate features — do not rejuvenate or over-smooth"
        )
    build_notes = {
        "slim": "preserve slender natural body proportions from the reference",
        "medium": "preserve natural body proportions from the reference",
        "full": "preserve fuller natural body proportions from the reference",
    }
    notes.append(build_notes[profile.build])
    return "; ".join(notes)


def _nanobanana_surreal_subjects(profile: "GuestProfile | None", is_group: bool) -> dict[str, str]:
    """Местоимения и субъекты для группового / одиночного кадра."""
    if is_group:
        n = profile.face_count if profile else 2
        return {
            "keep": (
                f"every visible person from the reference photo ({_nanobanana_group_size(n)}) — "
                "each person's identity, facial features, skin texture, hairstyle, expression, "
                "clothing and proportions"
            ),
            "place": "the group",
            "interact": "each person",
            "frame": "the group",
            "photoreal": "photorealistic people",
            "interaction_block": (
                "some abstract elements pass in front of bodies\n"
                "rings partially overlap arms and shoulders of different people\n"
                "bubble clusters wrap around the group\n"
                "foreground elements hide small parts of clothing on different people\n"
                "Each person can touch, hold, lean on, reach toward or rest on the abstract objects\n"
                "realistic depth and occlusion between people and objects\n"
                "strong integration between every person and the environment"
            ),
            "composition_extra": (
                "Camera pulled back — show everyone visible in the reference together in one cohesive frame.\n"
                "Do not drop anyone from the selfie, do not merge two people into one face, "
                "do not add extra people.\n"
                "Pose: friendly group selfie — warm genuine smiles, relaxed confident expressions, "
                "looking at the camera.\n"
            ),
            "identity_rule": (
                "Identity rule: every person from the reference must appear in the output, "
                "each recognizable — do not change ethnicity, age, gender, or face shape of anyone; "
                "do not merge faces, do not drop anyone, do not add extra people."
            ),
        }
    if profile is None:
        return {
            "keep": (
                "the same person from the reference photo — exact identity, facial features, "
                "skin texture, hairstyle, expression, clothing and natural proportions"
            ),
            "place": "the person",
            "interact": "the person",
            "frame": "the person",
            "photoreal": "photorealistic person",
            "interaction_block": (
                "some abstract elements pass in front of the body\n"
                "rings partially overlap arms and shoulders\n"
                "bubble clusters wrap around the figure\n"
                "foreground elements hide small parts of the clothing\n"
                "The person can touch, hold, lean on, reach toward or rest on the abstract objects\n"
                "realistic depth and occlusion\n"
                "strong integration between subject and environment"
            ),
            "composition_extra": "",
            "identity_rule": (
                "Identity rule: the output must look like the same guest from the reference — "
                "do not change ethnicity, age, gender, or face shape."
            ),
        }
    age = _age_phrase(profile)
    if profile.gender == "male":
        who = f"a boy ({age})" if profile.age_group == "child" else f"a man ({age})"
    elif profile.gender == "female":
        who = f"a girl ({age})" if profile.age_group == "child" else f"a woman ({age})"
    else:
        who = f"a person ({age})"
    profile_notes = _nanobanana_profile_identity_notes(profile)
    notes_suffix = f"; {profile_notes}" if profile_notes else ""
    return {
        "keep": (
            f"{who} from the reference photo — exact identity, facial features, skin texture, "
            f"hairstyle, expression, clothing and natural proportions{notes_suffix}"
        ),
        "place": "the person",
        "interact": "the person",
        "frame": "the person",
        "photoreal": "photorealistic person",
        "interaction_block": (
            "some abstract elements pass in front of the body\n"
            "rings partially overlap arms and shoulders\n"
            "bubble clusters wrap around the figure\n"
            "foreground elements hide small parts of the clothing\n"
            "The person can touch, hold, lean on, reach toward or rest on the abstract objects\n"
            "realistic depth and occlusion\n"
            "strong integration between subject and environment"
        ),
        "composition_extra": "",
        "identity_rule": (
            "Identity rule: the output must look like the same guest from the reference — "
            "do not change ethnicity, age, gender, or face shape."
        ),
    }


def _build_nanobanana_surreal_prompt(profile: "GuestProfile | None") -> str:
    """
    Premium surreal 3D editorial (Nano Banana / Gemini).
    Референс-фото передаётся отдельно; профиль гостя адаптирует блок identity.
    """
    is_group = profile is not None and profile.is_group()
    subj = _nanobanana_surreal_subjects(profile, is_group)

    return (
        "Transform the uploaded portrait into a premium surreal 3D editorial scene.\n\n"
        f"Keep {subj['keep']} unchanged.\n\n"
        f"Place {subj['place']} inside a vibrant abstract environment made of large glossy "
        "organic 3D shapes, inflatable forms, rounded blobs, soft tubular rings, bubble clusters, "
        "oversized flower-like balloon elements and reflective chrome spheres.\n\n"
        "Color palette:\n"
        "pastel aqua blue\n"
        "mint turquoise\n"
        "soft cyan\n"
        "neon-lime green\n"
        "fresh light green\n\n"
        "Materials:\n"
        "glossy smooth plastic\n"
        "translucent gel\n"
        "inflated vinyl\n"
        "soft-touch rubber\n"
        "fuzzy grass-like surfaces\n"
        "polished chrome metal spheres\n\n"
        f"The environment must physically interact with {subj['interact']}:\n"
        f"{subj['interaction_block']}\n\n"
        "Composition:\n"
        f"{subj['composition_extra']}"
        "Create a completely new composition every time.\n"
        "Do not repeat previous layouts.\n"
        "Use asymmetrical placement of shapes.\n"
        "Mix foreground, midground and background elements.\n"
        f"Large hero shapes should frame {subj['frame']}.\n\n"
        "Lighting:\n"
        "high-end advertising photography,\n"
        "soft studio lighting,\n"
        "bright pastel reflections,\n"
        "subtle rim light,\n"
        "clean highlights,\n"
        "luxury beauty campaign quality.\n\n"
        "Style references:\n"
        "modern CGI,\n"
        "premium 3D illustration,\n"
        "playful futuristic design,\n"
        "Apple-style cleanliness,\n"
        "Behance award-winning visual direction,\n"
        "surreal editorial portrait.\n\n"
        "Depth:\n"
        "strong foreground objects,\n"
        "layered composition,\n"
        "shallow depth of field,\n"
        "realistic shadows and contact lighting.\n\n"
        "Quality:\n"
        f"ultra detailed,\n"
        f"{subj['photoreal']},\n"
        "4K,\n"
        "commercial campaign quality,\n"
        "perfect compositing,\n"
        "seamless integration between photo and CGI environment.\n\n"
        "Vertical 9:16 portrait. "
        f"{subj['identity_rule']} "
        "Do not add text, logos, subtitles, or watermarks. Single cohesive image."
    )


def build_nanobanana_background_prompt() -> str:
    """Фон киоска: тот же surreal-стиль, без людей."""
    return (
        "Create a premium surreal 3D editorial environment scene with no people.\n\n"
        "A vibrant abstract environment made of large glossy organic 3D shapes, inflatable forms, "
        "rounded blobs, soft tubular rings, bubble clusters, oversized flower-like balloon elements "
        "and reflective chrome spheres.\n\n"
        "Color palette:\n"
        "pastel aqua blue\n"
        "mint turquoise\n"
        "soft cyan\n"
        "neon-lime green\n"
        "fresh light green\n\n"
        "Materials:\n"
        "glossy smooth plastic\n"
        "translucent gel\n"
        "inflated vinyl\n"
        "soft-touch rubber\n"
        "fuzzy grass-like surfaces\n"
        "polished chrome metal spheres\n\n"
        "Composition:\n"
        "Create a completely new composition every time.\n"
        "Do not repeat previous layouts.\n"
        "Use asymmetrical placement of shapes.\n"
        "Mix foreground, midground and background elements.\n"
        "Large hero shapes frame open negative space in the center for a future portrait.\n\n"
        "Lighting:\n"
        "high-end advertising photography,\n"
        "soft studio lighting,\n"
        "bright pastel reflections,\n"
        "subtle rim light,\n"
        "clean highlights,\n"
        "luxury beauty campaign quality.\n\n"
        "Style references:\n"
        "modern CGI,\n"
        "premium 3D illustration,\n"
        "playful futuristic design,\n"
        "Apple-style cleanliness,\n"
        "Behance award-winning visual direction,\n"
        "surreal editorial set design.\n\n"
        "Depth:\n"
        "strong foreground objects,\n"
        "layered composition,\n"
        "shallow depth of field,\n"
        "realistic shadows and contact lighting.\n\n"
        "Quality:\n"
        "ultra detailed,\n"
        "photoreal CGI,\n"
        "4K,\n"
        "commercial campaign quality.\n\n"
        "Vertical 9:16 portrait. "
        "No people, no faces, no human figures, no silhouettes, no body parts. "
        "Do not add text, logos, subtitles, or watermarks. Single cohesive image."
    )


def build_nanobanana_prompt(profile: "GuestProfile | None") -> str:
    """
    Финальный статичный кадр из nana-banana / Seedance брифа.
    Референс-фото передаётся отдельно в Gemini API.
    """
    from app.config import settings

    is_group = profile is not None and profile.is_group()
    style = (settings.nanobanana_style or "photoreal").strip().lower()
    if style in {"toon", "pixar", "cartoon", "3d"}:
        style = "toon"
    elif style in {"caricature", "caricatura", "funny", "humor", "sharzh", "grotesque"}:
        style = "caricature"

    if style == "photoreal":
        return _build_nanobanana_surreal_prompt(profile)

    subject = _nanobanana_subject(profile)
    if style == "caricature":
        if is_group:
            style_line = (
                "a bold grotesque festival caricature sharzh of the same recognizable people from the reference — "
                "strong editorial exaggeration on each face: enlarged distinctive features "
                "(nose, chin, jaw, forehead, ears, cheekbones) amplified from the reference, "
                "wide comic grins, squinting sparkling eyes, stretched proportions, punchy humorous distortion; "
                "hand-drawn ink outlines with gouache/watercolor festival poster rendering; "
                "each person instantly recognizable yet comically distorted; preserve ethnicity, age, gender "
                "and core likeness of everyone; do not merge faces, do not drop anyone; "
                "playful party sharzh, not horror, not hateful, not disgusting gore"
            )
        else:
            style_line = (
                "a bold grotesque festival caricature sharzh of the same recognizable person — "
                "strong editorial exaggeration: enlarge the most distinctive facial features from the reference "
                "(nose, chin, jaw, forehead, ears, cheekbones), wide comic grin, squinting sparkling eyes, "
                "stretched neck and head proportions, punchy humorous distortion; "
                "hand-drawn ink outlines with gouache/watercolor festival poster art; "
                "instantly recognizable yet comically distorted; preserve ethnicity, age, gender and core likeness; "
                "playful party sharzh, not horror, not hateful, not disgusting gore, not a different person"
            )
        scene = (
            "bright summer festival scene with glossy brand props, pink flowers, "
            "lime-green clover accents, floating balloons, black-and-white checkered ribbon, "
            "soft green glowing brand mark, emerald-to-turquoise gradient background, "
            "confetti sparks, saturated pop colors, caricature poster composition energy"
        )
        if is_group:
            scene_tail = (
                "Camera pulled back — whole group in one bold grotesque sharzh festival poster. "
                "High-contrast comic lighting, thick outlines, rich saturated colors, "
                "modern brand commercial, loud cheerful summer mood, every face sharp and expressive."
            )
        else:
            scene_tail = (
                "Camera pulled back — bold grotesque sharzh festival poster composition. "
                "High-contrast comic lighting, thick outlines, rich saturated colors, "
                "modern brand commercial, loud cheerful summer mood, sharp expressive face."
            )
    else:
        style_line = (
            "stylized as a Disney Pixar 3D animated character with glossy subsurface skin, "
            "soft cartoon proportions, organically embedded in the glossy 3D festival world"
        )
        scene = FESTIVAL_PORTRAIT_SCENE
        scene_tail = (
            "Camera pulled back to show the full festive composition. "
            "Bright daylight festival mood, even soft light on the face, rich saturated colors, "
            "modern brand commercial, happy summer mood, sharp focus on face, cinematic color grading."
        )

    if is_group:
        pose = (
            "Pose: friendly group selfie — everyone visible in the reference stands together, "
            "warm genuine smiles, relaxed confident expressions, looking at the camera."
        )
        identity = (
            "Identity rule: every person from the reference must appear in the output, "
            "each recognizable and only slightly more photogenic — "
            "do not change ethnicity, age, gender, or face shape of anyone; "
            "do not fuse two people into one face."
        )
    else:
        pose = "Pose: warm genuine smile, relaxed confident expression, looking at the camera."
        identity = (
            "Identity rule: the output must look like the same guest, only more photogenic — "
            "do not change ethnicity, age, gender, or face shape."
        )

    return (
        "Create one vertical 9:16 festival brand portrait — the final static frame (second 7–10) "
        "of a brand video, not a video strip.\n\n"
        f"Reference photo attached: keep {subject}. Render as {style_line}.\n\n"
        f"{pose}\n\n"
        f"Scene: {scene} "
        f"{scene_tail}\n\n"
        f"{identity}\n"
        "Do not add text, logos, subtitles, or watermarks. Single cohesive image."
    )

def build_festival_portrait_prompt(profile: "GuestProfile | None") -> tuple[str, str]:
    """
    Статичный финальный кадр (момент 7–10s брифа): гость в glossy 3D фестивальной сцене.
    Основано на промпте nana-banana / Seedance, без описания движения во времени.
    """
    subject = _subject_clause(profile)
    prompt = (
        "photorealistic vertical 9:16 festival brand portrait, final composed frame, "
        f"same person as reference, {subject}, "
        f"{FESTIVAL_PORTRAIT_SCENE}, "
        "camera pulled back to show the full festive composition, "
        "bright daylight festival mood, even soft light on the face, rich saturated colors, "
        "modern brand commercial, glossy 3D environment with photorealistic face, "
        "high detail, happy summer mood, sharp focus on face, cinematic color grading"
    )
    return prompt, FESTIVAL_PORTRAIT_NEGATIVE
