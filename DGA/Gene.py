import inspect
import time
import numpy as np
from abc import abstractmethod


### Initializers ###
class base_init_class:
  def run(self, shape: tuple) -> any:
    pass


class uniform_initialization(base_init_class):
  def __init__(self, min_val: float, max_val: float):
    self.min_val = min_val
    self.max_val = max_val

  def run(self, shape: tuple) -> np.ndarray:
    return np.random.uniform(low=self.min_val, high=self.max_val, size=shape)


class normal_initialization(base_init_class):
  def __init__(self, loc: float, scale: float):
    self.loc = loc
    self.scale = scale

  def run(self, shape: tuple) -> np.ndarray:
    return np.random.normal(loc=self.loc, scale=self.scale, size=shape)


### Mutation Functions ###
class base_mutate_class:
  def __init__(self, mutation_rate: float, decay: float = 1.0):
    self.mutation_rate = mutation_rate
    self.decay = decay

  def run(self, param: np.ndarray) -> np.ndarray:
    pass

  def decay_mutation_rate(self):
    self.mutation_rate *= self.decay


class no_mutation(base_mutate_class):
  def run(self, param: np.ndarray) -> np.ndarray:
    return param


class normal_mutation(base_mutate_class):
  def __init__(self, loc: float, scale: float, mutation_rate: float, decay: float = 1.0):
    super().__init__(mutation_rate, decay)
    self.loc = loc
    self.scale = scale

  def run(self, param: np.ndarray,) -> np.ndarray:
    if np.random.rand() < self.mutation_rate:
      return param + np.random.normal(loc=self.loc, scale=self.scale, size=param.shape)
    else:
      return param


class uniform_mutation(base_mutate_class):
  def __init__(self, min_val: float, max_val: float, mutation_rate: float, decay: float = 1.0):
    super().__init__(mutation_rate, decay)
    self.min_val = min_val
    self.max_val = max_val

  def run(self, param: np.ndarray) -> np.ndarray:
    if np.random.rand() < self.mutation_rate:
      return param + np.random.uniform(low=self.min_val, high=self.max_val, size=param.shape)
    else:
      return param


class splice_mutation(base_mutate_class):
  def __init__(self, mutation_rate: float, mutation_size: int, decay: float = 1.0, loc: float = 0, scale: float = 1):
    super().__init__(mutation_rate, decay)
    self.mutation_size = mutation_size
    self.loc = loc
    self.scale = scale

  def run(self, param: np.ndarray) -> np.ndarray:
    org_shape = param.shape
    if np.random.rand() < self.mutation_rate:
      mutation_start = np.random.randint(0, np.prod(param.shape))
      mutation_end = np.random.randint(mutation_start+1, mutation_start+2+self.mutation_size)
      if mutation_end > np.prod(param.shape):
        mutation_end = np.prod(param.shape)
      param = param.flatten()
      param[mutation_start:mutation_end] += np.random.normal(loc=self.loc, scale=self.scale, size=mutation_end-mutation_start)
      return param.reshape(org_shape)
    else:
      return param


### Crossover Functions ###
class base_crossover_class:
  def run(self, parents: list[np.ndarray]) -> np.ndarray:
    pass


class mean_crossover(base_crossover_class):
  def run(self, parents: list[np.ndarray]) -> np.ndarray:
    return np.mean(parents, axis=0)


class splice_crossover(base_crossover_class):
  def run(self, parents: list[np.ndarray]) -> np.ndarray:
    p1, p2 = parents[0], parents[1]
    full_index = np.prod(p1.shape)
    splice = np.random.randint(low=0, high=full_index)
    new_param = np.concatenate([p1.flatten()[:splice], p2.flatten()[splice:]])
    return new_param.reshape(p1.shape)


# Numerical representation of a Genome
# Generated by Genome, used to populate Model
class Parameters(dict):
  def __init__(self, iteration: int, values: dict = None,  # Numerical values as {gene_name: np.ndarray}
               fitness: float = None):
    super().__init__()
    self.iteration = iteration
    self.fitness = fitness
    self.timestamp = time.strftime('%H:%M:%S', time.localtime())

    if values is not None:
      self.update(values)  # Add values to self (dict)

    # Set hash (timestamp + iteration should be unique)
    hashable_obj = tuple([self.timestamp, self.iteration])
    self.hash_ = hash(hashable_obj)

    # Set tested flag if fitness provided
    if self.fitness is None:
      self.tested_ = False
    else:
      self.tested_ = True

  def as_array(self) -> np.ndarray:
    return np.concatenate([param.flatten() for param in self.values()])

  def set_fitness(self, fitness: float):
    self.fitness = fitness
    self.tested_ = True

  def set_iteration(self, iteration: int):
    self.iteration = iteration

  def set_timestamp(self, timestamp: float):
    self.timestamp = timestamp

  def set_tested(self, tested: bool):
    self.tested_ = tested

  def tested(self) -> bool:
    return self.tested_

  def set_attribute(self, name: str, value: any):
    setattr(self, name, value)

  def __hash__(self):
    return self.hash_


class Gene():
  def __init__(self,
               shape: tuple,
               dtype: type,
               default: any = None,
               min_val: float = -1,
               max_val: float = +1,
               **kwargs):
    self.shape = shape
    self.dtype = dtype
    self.default = default
    self.min_val = min_val
    self.max_val = max_val
    for key, val in kwargs.items():
      setattr(self, key, val)
    super().__init__()

  def to_json(self):
    attributes = {key: val for key, val in self.__dict__.items()}
    attributes['dtype'] = str(attributes['dtype'])
    return attributes


# During
# Take in set of genes, turn them
class Genome(dict):
  def __init__(self):
    super().__init__()

  def add_gene(self, gene: Gene, name: str):
    self[name] = gene

  # Take all values from a Parameters object and flatten them into a single 1D array
  def flatten_params(self, params: Parameters) -> np.ndarray:
    flattened_params = []
    for param in params.values():
      flattened_params.append(param.flatten())
    return np.concatenate(flattened_params)

  # Take a 1D array of values and unflatten them into a Parameters object
  def unflatten_params(self, flattened_params: np.ndarray) -> Parameters:
    params = Parameters()
    for key, gene in self.items():
      params[key] = flattened_params[:np.prod(gene.shape)].reshape(gene.shape)
      flattened_params = flattened_params[np.prod(gene.shape):]
    return params

  # Clamp parameter values within defined gene range
  def clamp_params(self, params: Parameters):
    for key, gene in self.items():
      params[key] = np.clip(params[key], gene.min_val, gene.max_val)

  def to_json(self):
    # json_genes = {key: gene.to_json() for key, gene in self.items()}
    return dict(self)

  @abstractmethod
  def initialize(self, iterations: int) -> Parameters:
    pass

  @abstractmethod
  def mutate(self, params: Parameters) -> Parameters:
    pass

  @abstractmethod
  def crossover(self, parents: list[Parameters], iterations: int) -> Parameters:
    pass


# class Gene:
#   def __init__(self,
#                shape: tuple,
#                datatype: type = float,
#                default: any = None,
#                # mutation_rate: float,
#                initializer: base_init_class = None,
#                mutator: base_mutate_class = None,
#                crosser: base_crossover_class = None,
#                **kwargs):
#     self.shape = shape
#     self.datatype = datatype
#     self.default = default
#     for key, val in kwargs.items():
#       setattr(self, key, val)
#
#     # Set initialization, mutation, and crossover functions
#     self.initializer = initializer
#     self.mutator = mutator
#     self.crosser = crosser
#
#     if self.initializer is not None:
#       self.init_arg_names = inspect.getfullargspec(self.initializer.run).args if self.initializer else None
#       self.init_args = {name : arg for name, arg in self.__dict__.items() if name in self.init_arg_names}
#
#     if self.mutator is not None:
#       self.mutate_arg_names = inspect.getfullargspec(self.mutator.run).args if self.mutator else None
#       self.mutate_args = {name : arg for name, arg in self.__dict__.items() if name in self.mutate_arg_names}
#
#     if self.crosser is not None:
#       self.crossover_arg_names = inspect.getfullargspec(self.crosser.run).args if self.crosser else None
#       self.crossover_args = {name : arg for name, arg in self.__dict__.items() if name in self.crossover_arg_names}
#
#   def to_json(self):
#     pass
#
#   def copy(self):
#     return Gene(shape=self.shape, datatype=self.datatype, default=self.default,
#                 initializer=self.initializer, mutator=self.mutator, crosser=self.crosser)
#
#
# class Genome(Gene, dict):
#   def __init__(self,
#                datatype: type = float,
#                default: any = None,
#                initializer: base_init_class = None,
#                mutator: base_mutate_class = None,
#                crosser: base_crossover_class = None,
#                **kwargs):
#     super().__init__(shape=None, datatype=datatype, default=default,
#                      initializer=initializer, mutator=mutator,
#                      crosser=crosser, **kwargs)
#
#   def add_gene(self, gene: Gene, name: str):
#     self[name] = gene
#
#   # Returns initializers for all genes
#   # Prioritize gene-level initializers, then genome-level
#   def get_initializers(self):
#     return {name: gene.initializer if gene.initializer is not None else self.initializer for name, gene in self.items()}
#
#   def get_mutators(self):
#     return {name: gene.mutator if gene.mutator is not None else self.mutator for name, gene in self.items()}
#
#   def get_crossers(self):
#     return {name: gene.crosser if gene.crosser is not None else self.crosser for name, gene in self.items()}
#
#   def get_run_args(self, gene_name: str, class_: callable) -> dict[str, any]:
#     gene = self[gene_name]
#     arg_names = inspect.getfullargspec(class_.run).args
#     arg_vals = {name: self.__dict__[name] if name in self.__dict__ else None for name in arg_names}
#     arg_vals = {name: gene.__dict__[name] if name in gene.__dict__ else None for name in arg_names}
#     if 'self' in arg_vals.keys():
#       del arg_vals['self']
#     return arg_vals
#
#   def initialize(self, iteration: int) -> Parameters:
#     new_params = Parameters(iteration=iteration)
#
#     # Set proper initializers & arguments for all genes
#     initializers = self.get_initializers()
#     # args = self.get_run_args(initializers)
#     for gene_name, initializer in initializers.items():
#       if initializer is None:
#         raise Exception(f"Genome initializer not defined for gene {gene_name}")
#
#       args = self.get_run_args(gene_name, initializer)
#       new_params[gene_name] = initializer.run(**args)
#
#     return new_params
#
#   def mutate(self, params: Parameters) -> any:
#     # Set proper mutators
#     mutators = self.get_mutators()
#     for gene_name, mutator in mutators.items():
#       if mutator is None:
#         raise Exception(f"Genome mutator not defined for gene {gene_name}")
#
#       args = self.get_run_args(gene_name, mutator)
#       if 'param' in args.keys():
#         del args['param']
#       params[gene_name] = mutator.run(params[gene_name], **args)
#     return params
#
#   def crossover(self, parents: list[Parameters], iteration: int) -> any:
#     new_params = Parameters(iteration=iteration)
#
#     # Set proper crossovers
#     crossovers = self.get_crossers()
#     # args = self.get_run_args(crossovers)
#     for gene_name, crossover in crossovers.items():
#       if crossover is None:
#         raise Exception(f"Genome crossover not defined for gene {gene_name}")
#
#       args = self.get_run_args(gene_name, crossover)
#       if 'parents' in args.keys():
#         del args['parents']
#       parent_params = [parent[gene_name] for parent in parents]
#       new_params[gene_name] = crossover.run(parent_params, **args)
#     return new_params
#
#   def decay_mutators(self):
#     mutators = self.get_mutators()
#     for mutator in mutators.values():
#       mutator.decay_mutation_rate()
#
#   def copy(self):
#     new_genome = Genome(shape=self.shape, datatype=self.datatype, default=self.default,
#                         initializer=self.initializer, mutator=self.mutator, crosser=self.crosser)
#     for name, gene in self.items():
#       new_genome.add_gene(gene.copy(), name)
#     return new_genome
