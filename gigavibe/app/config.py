from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    host: str = "0.0.0.0"
    port: int = 8765
    # auto — подставит LAN IP; иначе явный URL для QR (телефон гостя)
    public_base_url: str = "auto"
    hf_token: str | None = None

    # HTTPS: нужен, чтобы getUserMedia (камера) работал не только на localhost.
    # Самоподписанный сертификат генерируется scripts/gen_self_signed_cert.py
    use_https: bool = False
    ssl_certfile: Path | None = None
    ssl_keyfile: Path | None = None

    def effective_public_base_url(self) -> str:
        scheme = "https" if self.use_https else "http"
        if self.public_base_url.strip().lower() == "auto":
            from app.network import get_lan_ip

            ip = get_lan_ip()
            return f"{scheme}://{ip}:{self.port}"
        return self.public_base_url.rstrip("/")

    data_dir: Path = Path("data")
    output_ttl_hours: int = 24

    # ltx | svd | liveportrait | ref_video | festival_portrait | festival_toon | nanobanana | cinematic | auto
    generator_mode: str = "ltx"
    preload_model_on_startup: bool = True

    video_width: int = 720
    video_height: int = 1280
    video_fps: int = 30
    video_duration_sec: float = 10.0
    # H.264 после OpenCV (меньше CRF = лучше; 18 — визуально чище, чем 23)
    video_encode_crf: int = 18
    video_encode_preset: str = "medium"

    # ref_video: не апскейлить низкий референс; FPS как у исходного MP4
    ref_video_no_upscale: bool = True
    ref_video_use_source_fps: bool = True
    # Путь к весам face-swap. По умолчанию официальный inswapper_128.
    # Для inswapper_512 (выше нативное разрешение лица) укажите свой .onnx —
    # InsightFace сам прочитает input size из графа, менять код свопа не нужно.
    ref_video_swapper_path: Path = Path("models/inswapper_128.onnx")
    # После inswapper: GFPGAN (лицо чётче, +время на кадр).
    # На 512-свопе нужен меньше: можно держать слабее/реже (см. ref_video_restore_every_n).
    ref_video_face_restore: bool = True
    # Ускорение GFPGAN: прогонять через сеть каждый N-й кадр (keyframe), а для
    # промежуточных — добавлять интерполированный «детальный слой» (residual)
    # соседних keyframe'ов. 1 = обрабатывать каждый кадр (как раньше).
    ref_video_restore_every_n: int = 1
    # true — линейная интерполяция residual между keyframe'ами (плавнее);
    # false — держать residual ближайшего предыдущего keyframe (дешевле).
    ref_video_restore_interpolate: bool = True
    # Инлайн-restore (приём Rope): GFPGAN прогоняется ПРЯМО в swap-цикле по уже
    # известным kps лица (без повторной RetinaFace-детекции и без второго прохода
    # по MP4). Кадр не кодируется/декодируется между swap и restore — заметно
    # быстрее legacy-режима (отдельный restore_video_faces). false = старый путь.
    ref_video_inline_restore: bool = True
    # Сила GFPGAN при инлайн-restore (0..1): 1.0 — максимально «дочищает» лицо,
    # 0.5 — мягче, ближе к коже/текстуре свопа.
    ref_video_inline_restore_weight: float = 0.4
    # Прогон GFPGAN в fp16 на Ampere+ — быстрее, но на практике ломает качество (NaN/«нет restore»).
    ref_video_restore_fp16: bool = False
    # false = CPU diff-paste InsightFace (качество); true = быстрый GPU white-mask (квадрат).
    ref_video_gpu_paste: bool = False
    # Конвейер ref_video: legacy | rope_v1 (GPU diff-paste + ONNX GFPGAN 512 в swap).
    ref_video_pipeline: str = "rope_v1"
    # Порог diff-маски (0..100, как Rope DiffAmount); 10 ≈ insightface fthresh=10.
    ref_video_diff_amount: float = 10.0
    # restore: facexlib (GPU1, качество) | onnx_512 (ONNX на GPU1, быстрее, хуже лицо).
    ref_video_restore_engine: str = "facexlib"
    # true = CPU diff-paste после swap (качество) перед GFPGAN; false = GPU diff-paste.
    ref_video_swap_cpu_paste: bool = True
    ref_video_gfpgan_onnx_path: Path = Path("models/gfpgan/GFPGANv1.4.onnx")
    # Face parser (BiSeNet): маски глаз/рта — возврат оригинала референса поверх
    # свопа (приём VisoMaster), убирает артефакты GFPGAN на глазах и зубах.
    ref_video_face_parser: bool = False
    ref_video_parser_path: Path = Path("models/faceparser/faceparser_resnet34.onnx")
    ref_video_parser_eyes: bool = True
    ref_video_parser_mouth: bool = True
    # Сила возврата оригинала в зонах глаз/рта (0..1). 1 = полностью оригинал.
    ref_video_parser_strength: float = 0.8
    # Размытие краёв маски (меньше = строже зона, не растекается на брови).
    ref_video_parser_feather: int = 6
    # Число параллельных restore-воркеров на GPU1 (приём Rope: несколько
    # конвейеров на карту). restore (~155 мс/кадр) много медленнее swap, поэтому
    # пул из 2-3 GFPGAN-экземпляров прячет его за swap. Каждый воркер — свой
    # GFPGANer (face_helper не потокобезопасен). ~+1.5 ГБ VRAM на воркер.
    ref_video_restore_workers: int = 2
    # Две карты: inswapper+buffalo_l на swap, GFPGAN на restore (модели грузятся один раз при старте).
    ref_video_swap_device_id: int = 0
    ref_video_restore_device_id: int = 1
    # Data-parallel full-GPU (приём Rope-пула): список карт через запятую "0,1".
    # На каждой карте — самодостаточный комплект (детектор+inswapper+GFPGAN),
    # кадры делятся между картами. Пусто/одна карта → single-GPU inline.
    ref_video_gpu_devices: str = ""
    # ref_video: только face swap (+опц. GFPGAN), без шариков/атмосферы/фестивальной рамки
    ref_video_skip_festival_fx: bool = True

    # Движок свопа:
    #   "inswapper"      — стандартный InsightFace 128 (.get(), fp32)
    #   "inswapper_fast" — наш io-binding движок (fp16/fp32, приём Rope, быстрее)
    #   "simswap"        — нативный 512 (качество, медленнее)
    ref_video_swap_engine: str = "inswapper_fast"
    # Путь к модели для inswapper_fast. fp32 оставляем дефолтом: fp16 быстрее,
    # но на текущем стенде даёт заметное «мыло» лица.
    inswapper_fast_model_path: Path = Path("models/inswapper_128.onnx")
    # SimSwap 512: основной ONNX + отдельный ArcFace identity-энкодер (вход 112).
    simswap_model_path: Path = Path("models/simswap_512_beta.onnx")
    simswap_arcface_path: Path = Path("models/simswap_arcface.onnx")
    # Нормализация входа SimSwap (валидировать probe-скриптом; типичные: 0/1, 0.5/0.5).
    simswap_input_mean: float = 0.0
    simswap_input_std: float = 1.0

    # Безопасность внешних job: текущий RefVideoGenerator/InswapperEngine держит
    # singleton-модели и mutable io-binding buffers, поэтому несколько FastAPI jobs
    # одновременно сериализуем одним lock. Внутренний parallelism остаётся через
    # threaded_read + restore_workers.
    ref_video_serialize_jobs: bool = True
    # Зарезервировано под следующий Rope/VisoMaster-style шаг: bounded frame queue
    # + persistent swap workers. По умолчанию 1, потому что каждый worker должен
    # иметь собственный InswapperEngine/io-binding context; shared engine небезопасен.
    ref_video_swap_workers: int = 1

    # Конвейер свопа: отдельный поток-ридер декодирует кадры, пока GPU свопает (приём Rope).
    # Перекрывает IO-декодирование с GPU-вычислением → меньше простоя GPU.
    ref_video_threaded_read: bool = True
    ref_video_read_queue: int = 8

    # Детальный профиль этапов цикла (read/detect/swap/queue/assemble/write) в логи
    # и last_stage_timings. Диагностика узких мест — в проде держать выключенным.
    ref_video_profile: bool = False
    # Lean-детекция (приём Rope): на каждом кадре звать ТОЛЬКО детектор (det_10g),
    # а не весь buffalo_l (5 сетей). Для свопа нужны только kps — остальное лишнее.
    ref_video_lean_detect: bool = True
    # Размер входа det_10g (меньше = быстрее lean-detect; 512 обычно достаточно).
    ref_video_det_size: int = 512

    # SVD (8GB VRAM: 576x320, 14 frames — стабильно на 3060 Ti)
    svd_model_id: str = "stabilityai/stable-video-diffusion-img2vid-xt"
    svd_num_frames: int = 14
    svd_decode_chunk_size: int = 4
    svd_inference_steps: int = 20

    # LTX-Video (8GB VRAM + 16GB RAM: sequential offload, меньше кадров)
    ltx_model_id: str = "Lightricks/LTX-Video"
    # Папка с весами LTX. Можно вынести на другой диск (напр. D:) — модель ~20 ГБ.
    ltx_model_dir: Path = Path("models/LTX-Video")
    ltx_gguf_repo_file: str | None = "city96/LTX-Video-gguf/ltx-video-2b-v0.9-Q4_K_S.gguf"
    # fast | balanced | high — high дольше, но сильнее меняет сцену
    ltx_quality: str = "balanced"
    ltx_num_frames: int = 33
    ltx_inference_steps: int = 20
    ltx_guidance_scale: float = 3.0
    # guidance_rescale (0..1): лечит пересвет/дрейф цвета при длинной генерации. 0 = выкл.
    # Рекомендуемый рабочий диапазон 0.3-0.5 (см. подбор: рецепт P).
    ltx_guidance_rescale: float = 0.0
    ltx_decode_timestep: float | None = None
    ltx_decode_noise_scale: float | None = None
    ltx_distilled: bool = False
    # sequential — меньше пик RAM, чем enable_model_cpu_offload
    ltx_sequential_offload: bool = True
    # Стратегия размещения LTX в памяти:
    #   full              — вся модель резидентно на cuda:ltx_device_id (быстро, нужно ~10-12 ГБ VRAM)
    #   model_offload     — enable_model_cpu_offload (компромисс RAM/скорость)
    #   sequential_offload — enable_sequential_cpu_offload (мин. VRAM, очень медленно)
    # На 24 ГБ карте всегда выбирайте full — offload бессмысленно замедляет в разы.
    ltx_vram_strategy: str = "full"
    # GPU для LTX (cpu_offload.gpu_id). На машине с 2+ картами LTX держим на 0, InstantID на 1.
    ltx_device_id: int = 0
    # Пусто = промпты из app/prompts.py (по ТЗ PDF)
    ltx_prompt: str | None = None
    ltx_negative_prompt: str | None = None

    # Сценарий ТЗ: собрать фестивальную сцену → LTX → живая атмосфера → рамка
    festival_compose_scene: bool = True
    festival_atmosphere: bool = True
    festival_frame: bool = False

    # --- Ключевой кадр (стартовый кадр для LTX) ---
    # none        — подавать фото как есть
    # procedural  — текущий compose_festival_still (без нейросети)
    # instantid   — нейросетевой кадр SDXL+InstantID (стилизация с сохранением лица)
    keyframe_mode: str = "procedural"
    # InstantID / SDXL (модели крупные — храним на D:)
    instantid_base_model: str = "stabilityai/stable-diffusion-xl-base-1.0"
    instantid_base_dir: Path = Path("models/sdxl-base")
    instantid_repo_dir: Path = Path("models/InstantID")
    instantid_antelope_root: Path = Path("models/insightface_antelope")
    instantid_pipeline_dir: Path = Path("vendor/instantid")
    instantid_steps: int = 30
    instantid_guidance: float = 5.0
    # Сила сохранения личности (0..1) и влияние ControlNet-keypoints
    instantid_ip_scale: float = 0.8
    instantid_controlnet_scale: float = 0.8
    instantid_prompt: str | None = None
    instantid_negative_prompt: str | None = None
    # GPU для InstantID (cuda:N + onnxruntime ctx_id=N). На 2+ картах — 1 (LTX на 0).
    instantid_device_id: int = 0
    # true — НЕ выгружать SDXL+InstantID после ключевого кадра (держать резидентно на своей карте,
    # чтобы не перезагружать ~10 ГБ моделей на каждый запрос). Включать только если VRAM хватает
    # под InstantID и LTX одновременно (на разных картах).
    keyframe_keep_resident: bool = False

    # festival_toon: PuLID-FLUX fp8 (локально 8 GB: offload + fp8)
    pulid_flux_dir: Path = Path("vendor/pulid")
    pulid_flux_version: str = "v0.9.1"
    pulid_flux_steps: int = 20
    pulid_flux_guidance: float = 4.0
    pulid_flux_start_step: int = 1
    pulid_flux_id_weight: float = 0.85
    pulid_flux_true_cfg: float = 4.0
    pulid_flux_fp8: bool = True
    pulid_flux_offload: bool = True
    pulid_flux_aggressive_offload: bool = True
    pulid_flux_onnx_cpu: bool = True
    pulid_toon_prompt: str | None = None
    pulid_toon_negative: str | None = None

    # Nano Banana — внешняя генерация портрета (без локальной GPU)
    # aitunnel = AITunnel OpenAI Images API (рекомендуется, без VPN, ~15–40с)
    # quatarly = Quatarly OpenAI-compat
    # gemini   = Google Gemini API напрямую
    # proxy    = nanobananaapi.ai (async poll, ~100с)
    nanobanana_backend: str = "aitunnel"
    gemini_api_key: str | None = None
    gemini_api_base_url: str = ""
    aitunnel_api_key: str | None = None
    aitunnel_api_base_url: str = "https://api.aitunnel.ru/v1"
    quatarly_api_key: str | None = None
    quatarly_api_base_url: str = "https://api.quatarly.cloud/v1"
    nanobanana_model: str = "gemini-3.1-flash-image-preview"
    nanobanana_api_key: str | None = None
    nanobanana_api_base_url: str = "https://api.nanobananaapi.ai"
    # v2 = /generate-2 (рекомендуется) | v1 = /generate (IMAGETOIAMGE)
    nanobanana_api_version: str = "v2"
    nanobanana_aspect_ratio: str = "9:16"
    nanobanana_image_size: str = "1K"
    nanobanana_style: str = "photoreal"  # photoreal | toon | caricature (grotesque sharzh)
    nanobanana_prompt: str | None = None
    # Публичный URL киоска для imageUrls (если пусто — effective_public_base_url или 0x0.st)
    nanobanana_public_base_url: str = ""
    nanobanana_poll_sec: float = 2.0
    nanobanana_timeout_sec: float = 300.0
    nanobanana_jpeg_quality: int = 92
    # При сбое Quatarly (VPN/таймаут) — fallback на nanobananaapi.ai, если есть ключ
    nanobanana_fallback_to_proxy: bool = True

    # LivePortrait (отдельное venv: .venv-liveportrait)
    liveportrait_root: Path = Path("vendor/LivePortrait")
    # true — inference через gigavibe\.venv (без .venv-liveportrait, экономит ~3 GB)
    liveportrait_use_main_venv: bool = False
    liveportrait_python: str | None = None
    liveportrait_driving_path: Path | None = None
    liveportrait_driving_dir: Path = Path("assets/driving")
    driving_manifest_path: Path = Path("assets/driving/manifest.json")
    liveportrait_random_drive: bool = True
    liveportrait_driving_option: str = "expression-friendly"
    liveportrait_driving_multiplier: float = 0.95
    liveportrait_driving_max_sec: float = 10.0
    liveportrait_driving_smooth: float = 1e-4
    liveportrait_use_pkl_if_available: bool = True
    liveportrait_flag_crop_driving_video: bool = True
    # Атмосфера (зум/конфетти) поверх LP часто даёт «мельтешение» — по умолчанию выкл.
    liveportrait_festival_atmosphere: bool = False
    liveportrait_flag_stitching: bool = True
    liveportrait_flag_do_torch_compile: bool = False
    liveportrait_device_id: int = 0
    liveportrait_timeout_sec: int = 600

    brand_overlay_path: Path | None = None
    background_music_path: Path | None = None

    # Киоск: автокамера, снимок по улыбке (пороги для фронта)
    kiosk_auto_camera: bool = True
    kiosk_camera_width: int = 1920
    kiosk_camera_height: int = 1080
    kiosk_smile_capture: bool = True
    kiosk_smile_threshold: float = 0.42
    kiosk_smile_hold_frames: int = 12
    kiosk_smile_hold_ms: int = 650
    kiosk_smile_detect_stride: int = 6
    kiosk_smile_cooldown_ms: int = 8000
    kiosk_face_min_size: float = 0.12
    kiosk_face_hold_frames: int = 12
    kiosk_face_release_frames: int = 20
    kiosk_face_hold_ms: int = 700
    kiosk_face_release_ms: int = 1600
    kiosk_face_detect_stride: int = 25
    kiosk_jpeg_quality: float = 0.96
    # true — на экране результата показывать время генерации (для стенда/отладки)
    kiosk_test_mode: bool = False

    # Возраст гостя (InsightFace genderage): child ≤ child_max, senior ≥ senior_min
    guest_age_child_max: int = 15
    guest_age_senior_min: int = 55
    # Детекция нескольких лиц в групповом селфи (InsightFace det_10g)
    guest_face_det_size: int = 960
    guest_face_det_thresh: float = 0.25
    # Второе лицо считаем только если его bbox ≥ доля от крупнейшего (отсекает шум)
    guest_face_min_relative_size: float = 0.12

    # Отправка готового файла на внешний сервер (multipart POST)
    output_upload_enabled: bool = False
    output_upload_url: str | None = None
    output_upload_api_key: str | None = None
    # bearer | x-api-key
    output_upload_auth: str = "bearer"
    output_upload_timeout_sec: float = 60.0
    output_upload_chunk_size: int = 262144
    output_upload_max_retries: int = 5
    output_upload_retry_delay_sec: float = 3.0

    # QR ведёт на внешний сервер фото (если пусто — PUBLIC_BASE_URL / auto)
    qr_public_base_url: str = ""

    # Печать на локальном принтере (Windows, mspaint /pt)
    print_enabled: bool = False
    print_printer_name: str | None = None
    print_only_images: bool = True
    print_after_upload: bool = True
    print_timeout_sec: float = 120.0
    print_width_mm: float = 100.0
    print_height_mm: float = 150.0
    print_dpi: int = 300
    print_scale: float = 1.0
    print_offset_x_mm: float = 0.0
    print_offset_y_mm: float = 0.0
    print_frame_path: Path | None = Path("web/assets/print/gigavibe-frame-10x15.png")
    # Не останавливать job при сбое upload/print (киоск продолжит показ QR)
    output_dispatch_fail_open: bool = True


settings = Settings()
settings.data_dir.mkdir(parents=True, exist_ok=True)
(settings.data_dir / "jobs").mkdir(parents=True, exist_ok=True)
(settings.data_dir / "outputs").mkdir(parents=True, exist_ok=True)
