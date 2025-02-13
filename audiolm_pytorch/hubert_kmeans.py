from pathlib import Path

import torch
from torch import nn
from einops import rearrange, pack, unpack

import joblib
import fairseq

class HubertWithKmeans(nn.Module):
    def __init__(
        self,
        checkpoint_path,
        kmeans_path
    ):
        super().__init__()
        model_path = Path(checkpoint_path)
        kmeans_path = Path(kmeans_path)

        assert model_path.exists(), f'path {checkpoint_path} does not exist'
        assert kmeans_path.exists(), f'path {kmeans_path} does not exist'

        checkpoint = torch.load(checkpoint_path)
        load_model_input = {checkpoint_path: checkpoint}
        model, *_ = fairseq.checkpoint_utils.load_model_ensemble_and_task(load_model_input)

        self.model = model[0]
        self.model.eval()

        kmeans = joblib.load(kmeans_path)
        self.kmeans = kmeans

    @property
    def groups(self):
        return 1

    @property
    def codebook_size(self):
        return self.kmeans.n_clusters

    @torch.no_grad()
    def forward(self, wav_input, flatten = True):
        device = wav_input.device

        embed = self.model(wav_input, features_only = True)
        embed, packed_shape = pack([embed['x']], '* d')

        codebook_indices = self.kmeans.predict(embed.cpu().detach().numpy())

        codebook_indices = torch.from_numpy(codebook_indices).to(device).long()

        if flatten:
            return codebook_indices

        codebook_indices, = unpack(codebook_indices, packed_shape, '*')
        return codebook_indices
