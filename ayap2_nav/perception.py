"""AYAP-2 perception modulu.

Bu dosya sadece goruntu tabanli kaya/engel segmentasyonundan sorumludur.
Notebook'tan alinmis U-Net + VGG16 transfer learning mimarisi,
egitim kodlari olmadan burada inference amacli tutulur.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np


def ModelEnhancer(
    input_shape: tuple[int, int, int] = (500, 500, 3),
    vgg16_weights: str = "imagenet",
) -> object:
    """Notebook'taki U-Net + VGG16 model mimarisini olusturur.

    Not:
        Egitim asamasi bu projeye dahil edilmez. Bu fonksiyon sadece
        mimariyi kurmak icin kullanilir.
    """
    try:
        import tensorflow as tf
    except ModuleNotFoundError as err:
        raise ModuleNotFoundError(
            "Perception modeli icin 'tensorflow' gereklidir. "
            "Ornek kurulum: pip install tensorflow"
        ) from err

    layers = tf.keras.layers
    vgg16 = tf.keras.applications.vgg16

    VGG16 = vgg16.VGG16(
        include_top=False,
        weights=vgg16_weights,
        input_shape=input_shape,
    )
    last_layer = VGG16.output

    for layer in VGG16.layers:
        if layer.name in {
            "block1_pool",
            "block2_pool",
            "block3_pool",
            "block4_pool",
            "block5_pool",
        }:
            layer.trainable = False

    model_ = layers.Conv2DTranspose(256, (3, 3), strides=(2, 2))(last_layer)
    model_ = layers.LeakyReLU(0.1)(model_)
    model_ = layers.BatchNormalization()(model_)

    concat_1 = layers.concatenate([model_, VGG16.get_layer("block5_conv3").output])

    model_ = layers.Conv2D(512, (3, 3), strides=(1, 1), padding="same")(concat_1)
    model_ = layers.LeakyReLU(0.1)(model_)
    model_ = layers.BatchNormalization()(model_)

    model_ = layers.Conv2DTranspose(512, (3, 3), strides=(2, 2), padding="same")(model_)
    model_ = layers.LeakyReLU(0.1)(model_)
    model_ = layers.BatchNormalization()(model_)

    concat_2 = layers.concatenate([model_, VGG16.get_layer("block4_conv3").output])

    model_ = layers.Conv2D(512, (3, 3), strides=(1, 1), padding="same")(concat_2)
    model_ = layers.LeakyReLU(0.1)(model_)
    model_ = layers.BatchNormalization()(model_)

    model_ = layers.Conv2DTranspose(512, (3, 3), strides=(2, 2))(model_)
    model_ = layers.LeakyReLU(0.1)(model_)
    model_ = layers.BatchNormalization()(model_)

    concat_3 = layers.concatenate([model_, VGG16.get_layer("block3_conv3").output])

    model_ = layers.Conv2D(256, (3, 3), strides=(1, 1), padding="same")(concat_3)
    model_ = layers.LeakyReLU(0.1)(model_)
    model_ = layers.BatchNormalization()(model_)

    model_ = layers.Conv2DTranspose(256, (3, 3), strides=(2, 2), padding="same")(model_)
    model_ = layers.LeakyReLU(0.1)(model_)
    model_ = layers.BatchNormalization()(model_)

    concat_4 = layers.concatenate([model_, VGG16.get_layer("block2_conv2").output])

    model_ = layers.Conv2D(128, (3, 3), strides=(1, 1), padding="same")(concat_4)
    model_ = layers.LeakyReLU(0.1)(model_)
    model_ = layers.BatchNormalization()(model_)

    model_ = layers.Conv2DTranspose(128, (3, 3), strides=(2, 2), padding="same")(model_)
    model_ = layers.LeakyReLU(0.1)(model_)
    model_ = layers.BatchNormalization()(model_)

    concat_5 = layers.concatenate([model_, VGG16.get_layer("block1_conv2").output])

    model_ = layers.Conv2D(64, (3, 3), strides=(1, 1), padding="same")(concat_5)
    model_ = layers.LeakyReLU(0.1)(model_)
    model_ = layers.BatchNormalization()(model_)

    model_ = layers.Conv2D(3, (3, 3), strides=(1, 1), padding="same")(model_)
    model_ = layers.LeakyReLU(0.1)(model_)
    model_ = layers.BatchNormalization()(model_)

    return tf.keras.Model(VGG16.input, model_)


class RockSegmentationPerception:
    """Kaya/engel segmentasyon modelini lazy-load ederek inference yapar."""

    def __init__(
        self,
        *,
        weights_path: str | Path,
        input_shape: tuple[int, int, int] = (500, 500, 3),
        vgg16_weights: str = "imagenet",
    ) -> None:
        self.input_shape = input_shape
        self.vgg16_weights = vgg16_weights
        self.weights_path = self._resolve_weights_path(weights_path)
        self._model: object | None = None

    def _resolve_weights_path(self, weights_path: str | Path) -> Path:
        """Goreli/verilen agirlik yolunu proje baglaminda cozer."""
        p = Path(weights_path).expanduser()
        if p.is_absolute():
            return p

        here = Path(__file__).resolve().parent
        candidates = [
            Path.cwd() / p,
            here / p,
            here.parent / p,
            here / "models" / p,
            here.parent / "models" / p,
        ]
        for cand in candidates:
            if cand.exists():
                return cand.resolve()

        return p

    def _ensure_model_loaded(self) -> None:
        """Modeli ilk inference aninda RAM'e yukler."""
        if self._model is not None:
            return

        model = ModelEnhancer(
            input_shape=self.input_shape,
            vgg16_weights=self.vgg16_weights,
        )

        if not self.weights_path.exists():
            raise FileNotFoundError(
                "Segmentasyon agirlik dosyasi bulunamadi: "
                f"{self.weights_path}. "
                "config.SEGMENTATION_MODEL_WEIGHTS yolunu guncelleyin."
            )

        try:
            model.load_weights(str(self.weights_path))
        except Exception as original_err:
            # Notebook'taki ModelCheckpoint ciktisi cogunlukla tam model (.h5)
            # oldugu icin, ikinci adimda modeli yukleyip sadece agirliklari
            # mevcut mimariye transfer etmeyi dene.
            suffix = self.weights_path.suffix.lower()
            if suffix != ".h5":
                raise RuntimeError(
                    "Agirliklar ModelEnhancer mimarisine yuklenemedi: "
                    f"{self.weights_path}"
                ) from original_err

            try:
                import tensorflow as tf
            except ModuleNotFoundError as err:
                raise ModuleNotFoundError(
                    "'.h5' dosyasindan model yuklemek icin 'tensorflow' gereklidir."
                ) from err

            loaded = tf.keras.models.load_model(str(self.weights_path), compile=False)
            model.set_weights(loaded.get_weights())

        self._model = model

    @staticmethod
    def _prediction_to_score(prediction: np.ndarray) -> np.ndarray:
        """3-kanalli model cikisini tek kanalli obstacle skora donusturur."""
        if prediction.ndim != 3:
            raise ValueError(
                "Model cikisi 3D olmali (H, W, C), "
                f"elde edilen boyut: {prediction.shape}"
            )

        score = np.mean(prediction.astype(np.float32), axis=2)

        # Cikis dagilimi egitimde sigmoid ile sinirlanmamis olabilecegi icin
        # robust bir 0..1 olcekleme uygula.
        p_low = float(np.percentile(score, 2.0))
        p_high = float(np.percentile(score, 98.0))
        span = max(p_high - p_low, 1e-9)
        score = (score - p_low) / span
        return np.clip(score, 0.0, 1.0)

    def _preprocess_frame(self, frame_bgr: np.ndarray) -> np.ndarray:
        """OpenCV BGR frame'i notebook ile uyumlu model girdisine cevirir."""
        try:
            import cv2
        except ModuleNotFoundError as err:
            raise ModuleNotFoundError(
                "Kamera tabanli inference icin 'opencv-python' gereklidir."
            ) from err

        if frame_bgr.ndim != 3 or frame_bgr.shape[2] != 3:
            raise ValueError(
                "Frame 3 kanalli olmali (H, W, 3), "
                f"elde edilen boyut: {frame_bgr.shape}"
            )

        h_in, w_in, _ = self.input_shape
        frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        resized = cv2.resize(frame_rgb, (w_in, h_in), interpolation=cv2.INTER_LINEAR)

        return resized.astype(np.float32).reshape(1, h_in, w_in, 3)

    def segment_rocks(
        self,
        frame_bgr: np.ndarray,
        *,
        threshold: float = 0.55,
        output_shape: tuple[int, int] | None = None,
    ) -> np.ndarray:
        """Tek frame'de kaya/engel maskesi uretir.

        Returns:
            np.uint8 mask (0/1), varsayilan model cozunurlugunde ya da
            output_shape verilirse hedef grid boyutunda.
        """
        self._ensure_model_loaded()
        assert self._model is not None

        batch = self._preprocess_frame(frame_bgr)
        prediction = self._model.predict(batch, verbose=0)[0]
        score = self._prediction_to_score(prediction)

        mask = (score >= float(threshold)).astype(np.uint8)

        if output_shape is not None and tuple(mask.shape) != tuple(output_shape):
            try:
                import cv2
            except ModuleNotFoundError as err:
                raise ModuleNotFoundError(
                    "Maskeyi hedef grid boyutuna yeniden olceklemek icin "
                    "'opencv-python' gereklidir."
                ) from err

            out_rows, out_cols = int(output_shape[0]), int(output_shape[1])
            mask = cv2.resize(
                mask,
                (out_cols, out_rows),
                interpolation=cv2.INTER_NEAREST,
            ).astype(np.uint8)

        return mask
