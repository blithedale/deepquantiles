from keras.layers import Input, Dense
from keras.models import Model
from keras.optimizers import Adam
from sklearn.base import BaseEstimator

from .losses import MDNLossLayer, keras_mean_pred_loss


class MixtureDensityRegressor(BaseEstimator):
    """Fit a Mixture Density Network (MDN)."""

    def __init__(
        self,
        shared_units=(8, 8),
        weight_units=(8, ),
        mu_units=(8, ),
        sigma_units=(8, ),
        activation='relu',
        n_components=3,
        lr=0.001,
        epochs=10,
        batch_size=100
    ):
        self._model_instance = None
        self.shared_units = shared_units
        self.weight_units = weight_units
        self.mu_units = mu_units
        self.sigma_units = sigma_units
        self.activation = activation
        self.n_components = n_components
        self.lr = lr
        self.epochs = epochs
        self.batch_size = batch_size

    def _model(self):
        input_features = Input((1, ), name='X')
        input_label = Input((1, ), name='y')

        # append final output
        intermediate = input_features
        for idx, units in enumerate(self.shared_units):
            intermediate = Dense(
                units=units, activation=self.activation, name=f'dense_{idx}'
            )(intermediate)

        weight, mu, sigma = intermediate, intermediate, intermediate

        for idx, units in enumerate(self.weight_units):
            weight = Dense(units, activation=self.activation, name=f'weight_dense_{idx}')(weight)

        weight = Dense(self.n_components, activation='softmax', name='weight_output')(weight)

        for idx, units in enumerate(self.mu_units):
            mu = Dense(units, activation=self.activation, name=f'mu_dense_{idx}')(mu)

        mu = Dense(self.n_components, activation=None, name='mu_output')(mu)

        for idx, units in enumerate(self.sigma_units):
            sigma = Dense(units, activation=self.activation, name=f'sigma_dense_{idx}')(sigma)

        sigma = Dense(self.n_components, activation='relu', name='sigma_output')(sigma)

        mdn_model = Model(input_features, [weight, mu, sigma], name='MDN')

        loss_output = MDNLossLayer([input_label, weight, mu, sigma])

        loss_model = Model([input_features, input_label], loss_output)
        loss_model.compile(optimizer=Adam(lr=self.lr), loss=keras_mean_pred_loss)

        return {'loss': loss_model, 'mdn': mdn_model}

    def _init_model(self):
        self._model_instance = self._model()
        return self._model_instance

    @property
    def model(self):
        return self._model_instance or self._init_model()

    def fit(self, X, y, **kwargs):
        self._init_model()
        fit_kwargs = dict(
            epochs=self.epochs,
            batch_size=self.batch_size,
        )
        fit_kwargs.update(kwargs)
        self.model['loss'].fit([X, y], 0 * y, **fit_kwargs)

    def predict(self, X, **kwargs):
        predict_kwargs = dict(batch_size=self.batch_size, )
        predict_kwargs.update(kwargs)
        w, mu, sigma = self.model['mdn'].predict(X, **predict_kwargs)
        return w, mu, sigma

    def predict_mean(self, X, **kwargs):
        w, mu, sigma = self.predict(X, **kwargs)
        mean = (w * mu).sum(axis=1)
        return mean

    def sample(self, X, num_samples=10, **kwargs):
        w, mu, sigma = self.predict(X, **kwargs)
        raise NotImplementedError
