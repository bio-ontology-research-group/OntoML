from mowl.base_models.model import EmbeddingModel
import torch as th
from torch.utils.data import DataLoader, default_collate
from mowl.datasets.alc import ALCDataset


class EmbeddingALCModel(EmbeddingModel):
    """Abstract class that provides basic functionalities for methods that aim to embed ALC \
    language.

    """

    def __init__(self, dataset, batch_size, model_filepath=None, device="cpu"):
        super().__init__(dataset, model_filepath=model_filepath)

        if not isinstance(batch_size, int):
            raise TypeError("Parameter batch_size must be of type int.")

        if not isinstance(device, str):
            raise TypeError("Optional parameter device must be of type str.")

        self._datasets_loaded = False
        self._dataloaders_loaded = False
        self.batch_size = batch_size
        self.device = device

        self._training_datasets = None
        self._validation_datasets = None
        self._testing_datasets = None

    def _load_datasets(self):
        """This method will create different data attributes and finally the corresponding \
            DataLoaders for each axiom pattern in each subset (training, validation and testing).
        """
        if self._datasets_loaded:
            return

        training_dataset = ALCDataset(
            self.dataset.ontology, self.dataset, device=self.device)
        self._training_datasets = training_dataset.get_datasets()

        self._validation_datasets = None
        if self.dataset.validation:
            validation_dataset = ALCDataset(
                self.dataset.validation, self.dataset,  device=self.device)
            self._validation_datasets = validation_dataset.get_datasets()

        self._testing_datasets = None
        if self.dataset.testing:
            testing_dataset = ALCDataset(
                self.dataset.testing, self.dataset, device=self.device)

            self._testing_datasets = testing_el_dataset.get_datasets()

        self._datasets_loaded = True

    def _load_dataloaders(self):
        if self._dataloaders_loaded:
            return

        self._load_datasets()

        self._training_dataloaders = {
            k: DataLoader(v, batch_size=self.batch_size) for k, v in
            self._training_datasets.items()}

        if self._validation_datasets:
            self._validation_dataloaders = {
                k: DataLoader(v, batch_size=self.batch_size) for k, v in
                self._validation_datasets.items()}

        if self._testing_datasets:
            self._testing_dataloaders = {
                k: DataLoader(v, batch_size=self.batch_size) for k, v in
                self._testing_datasets.items()}

        self._dataloaders_loaded = True

    @property
    def training_datasets(self):
        """Returns the training datasets for each GCI type. Each dataset is an instance \
of :class:`mowl.datasets.el.ELDataset`

        :rtype: dict
        """
        self._load_datasets()
        return self._training_datasets

    @property
    def validation_datasets(self):
        """Returns the validation datasets for each GCI type. Each dataset is an instance \
of :class:`mowl.datasets.el.ELDataset`

        :rtype: dict
        """
        if self.dataset.validation is None:
            raise AttributeError("Validation dataset is None.")

        self._load_datasets()
        return self._validation_datasets

    @property
    def testing_datasets(self):
        """Returns the testing datasets for each GCI type. Each dataset is an instance \
of :class:`mowl.datasets.el.ELDataset`

        :rtype: dict
        """
        if self.dataset.testing is None:
            raise AttributeError("Testing dataset is None.")

        self._load_datasets()
        return self._testing_datasets

    @property
    def training_dataloaders(self):
        """Returns the training dataloaders for each GCI type. Each dataloader is an instance \
of :class:`torch.utils.data.DataLoader`

        :rtype: dict
        """
        self._load_dataloaders()
        return self._training_dataloaders

    @property
    def validation_dataloaders(self):
        """Returns the validation dataloaders for each GCI type. Each dataloader is an instance \
of :class:`torch.utils.data.DataLoader`

        :rtype: dict
        """
        if self.dataset.validation is None:
            raise AttributeError("Validation dataloader is None.")

        self._load_dataloaders()
        return self._validation_dataloaders

    @property
    def testing_dataloaders(self):
        """Returns the testing dataloaders for each GCI type. Each dataloader is an instance \
of :class:`torch.utils.data.DataLoader`

        :rtype: dict
        """
        if self.dataset.testing is None:
            raise AttributeError("Testing dataloader is None.")

        self._load_dataloaders()
        return self._testing_dataloaders
