from functools import cache
import os
from datetime import datetime
import json
from pathlib import Path
from typing import Annotated, Callable, Any, NamedTuple
from dataclasses import dataclass, field
import tracemalloc


import torch
from torch.utils.data import Dataset, DataLoader
from transformers import OpenAIGPTLMHeadModel, OpenAIGPTConfig
from muutils.logger import Logger, TimerContext
from muutils.json_serialize import json_serialize, dataclass_serializer_factory
from muutils.misc import sanitize_fname
from muutils.tensor_utils import ATensor
from muutils.statcounter import StatCounter

from maze_transformer.training.dataset import DatasetConfig

TokenizerFunction = Callable[[list[str]], list[int]]

@dataclass(frozen=True, kw_only=True)
class BaseGPTConfig:
	"""gpt model config without vocab size, context size, or padding token"""
	n_embed: int = 128
	n_layer: int = 8
	n_head: int = 4
	_kwargs: dict = field(default_factory=dict)

	def as_dict(self) -> dict:
		return dict(
			**{
				k: getattr(self, k)
				for k in self.__dataclass_fields__ 
				if k != "_kwargs"
			},
			**self._kwargs,
		)

	def serialize(self) -> str:
		return self.as_dict()

@dataclass(kw_only=True)
class TrainConfig:
	"""full training configuration"""
	name: str

	base_gpt_cfg: BaseGPTConfig
	# wandb_proj: str|None = None
	device: Annotated[torch.device, "device to use for training"] = torch.device(
		# "cuda" if torch.cuda.is_available() else "cpu"
		"cuda:0"
	)

	max_samples: int|None = None
	epochs: int = 1
	optimizer: torch.optim.Optimizer = torch.optim.RMSprop
	optimizer_kwargs: dict[str, Any] = field(
		default_factory = lambda : dict(lr = 0.000001)
	)
	batch_size: int = 128

	dataloader_cfg: dict = field(default_factory = lambda : dict(
		shuffle = True,
		num_workers = 16, # make this smaller if you're not running on a big cluster probably
		persistent_workers = True,
		drop_last = True,
		# collate_fn = None, # we pad the tensors in the Dataset object
		# batch_size = None, # see batchsize in the encompassing TrainConfig
	))

	print_loss_interval: int = 1000
	checkpoint_interval: int = 50000

	# n_ctx: int = property(lambda self: self.model_config.n_ctx)
	_gpt_config_ctor_kwargs: dict = field(default_factory=dict)
	
	def get_gpt_config(
			self, 
			**kwargs,
		) -> OpenAIGPTConfig:

		self._gpt_config_ctor_kwargs = {
			**self.base_gpt_cfg.as_dict(),
			**kwargs,
			**dict(device = self.device),
		}

		return OpenAIGPTConfig(**self._gpt_config_ctor_kwargs)

TrainConfig.serialize = dataclass_serializer_factory(
	TrainConfig,
	special_serializers=dict(
		# gpt_config = lambda self: json_serialize(self.get_gpt_config().to_dict()),
		_optimizer_name = lambda self: self.optimizer.__name__,
		base_gpt_cfg = lambda self: self.base_gpt_cfg.as_dict,
	),
	fields_exclude=["optimizer"],
)


TrainingSetup = NamedTuple("TrainingSetup", [
	("data_cfg", DatasetConfig),
	("train_cfg", TrainConfig),
	("model_cfg", OpenAIGPTConfig),
	("logger", Logger),
	("basepath_train", Path),
])

def setup_train(
		basepath: Path, 
		train_cfg: TrainConfig,
		data_cfg_class: type = DatasetConfig,
		data_cfg_fname: str = "cfg.json",
		**cfg_kwargs,
	) -> tuple[DatasetConfig, Logger, Path]:

	basepath = Path(basepath)

	# load the dataset config
	cfg_path: Path = Path(basepath) / data_cfg_fname
	with open(cfg_path, "r") as f:
		data_cfg: data_cfg_class = data_cfg_class.load(json.load(f))
	data_cfg.name = f"{sanitize_fname(data_cfg.name)}_{datetime.now().strftime('%Y-%m-%d-%H-%M-%S')}"

	# set up paths
	basepath_train: Path = basepath / data_cfg.name
	os.makedirs(basepath_train, exist_ok = True)
	with open(basepath_train / "config.json", "w") as f:
		json.dump(json_serialize(data_cfg), f, indent = "\t")

	# set up logger
	logger: Logger = Logger(
		log_path=Path(basepath_train / "log.jsonl").as_posix(),
		console_print_threshold=30,
		stream_default_levels={"log_config": 40, "train": 50, "mem_usage": 40},
		stream_default_contents={"mem_usage": {"traced_memory": (
			lambda : dict(zip(("current", "peak"), tracemalloc.get_traced_memory()))
		)}},
	)

	# set up the training config
	model_cfg: OpenAIGPTConfig = train_cfg.get_gpt_config(
		**dict(data_cfg.gpt_config_kwargs),
		device = train_cfg.device,
	)

	logger.log("loaded data config, initialized logger")
	logger.log_config(dict(data_cfg = json_serialize(data_cfg)))
	logger.log_config(dict(train_cfg = json_serialize(train_cfg)))
	logger.log_config(dict(base_model_cfg = json_serialize(train_cfg._gpt_config_ctor_kwargs))) # pylint: disable=protected-access
	# logger.log_config(dict(model_cfg = json_serialize(model_cfg)))
	logger.log_config(dict(logger_cfg =
		{
			"data_cfg.name": data_cfg.name,
			"train_cfg.name": train_cfg.name,
			"basepath": basepath,
			"basepath_train": basepath_train,
			"log_file": logger._log_path,
			"model_cfg.device": model_cfg.device,
		},
		lvl = 0,
	))

	return TrainingSetup(
		data_cfg = data_cfg,
		train_cfg = train_cfg,
		model_cfg = model_cfg,
		logger = logger,
		basepath_train = basepath_train,
	)