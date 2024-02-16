import time
import numpy as np

# Object containing numeric information for a model (the models 'parameters')
# Generated by Genome
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

  # Convert self to flattened-numpy array representation
  def as_array(self) -> np.ndarray:
    return np.concatenate([param.flatten() for param in self.values()])

  # Convert flattened-numpy array to Parameters object
  def from_array(self, array: np.ndarray):
    index = 0
    for gene_name, gene in self.items():
      gshape = gene.shape
      gsize = np.prod(gshape)
      self[gene_name] = array[index:index+gsize].reshape(gshape)
      index += gsize

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


# Subsection of genome. Object contains basic information about that subsection
class Gene():
  def __init__(self,
               dtype: type,
               default: any = None,
               min_val: float = -1,
               max_val: float = +1,
               shape: tuple = None,
               mutation_rate: float = 0.5,
               mutation_scale: float = 0.1,
               **kwargs):
    self.shape = shape
    self.dtype = dtype
    self.default = default
    self.min_val = min_val
    self.max_val = max_val
    self.mutation_rate = mutation_rate
    self.mutation_scale = mutation_scale
    for key, val in kwargs.items():
      setattr(self, key, val)

    # Lock min-max if type is bool
    if dtype == bool:
      self.min_val = 0
      self.max_val = 1
    super().__init__()

  def to_json(self):
    attributes = {key: val for key, val in self.__dict__.items()}
    attributes['dtype'] = str(attributes['dtype'])
    return attributes


# Object containing all genes for a model. Specifies how to initialize, mutate, and crossover values
# Generates Parameter objects
class Genome(dict):
  def __init__(self):
    super().__init__()

  def add_gene(self, gene: Gene, name: str):
    self[name] = gene

  # Called when a new Parameters is needed, and no other Parameters in pool
  # Inputs: iteration
  # Outputs: new Parameters
  def initialize(self, iteration: int) -> Parameters:
    new_params = Parameters(iteration=iteration)
    for gene_name, gene in self.items():
      gdefault = gene.default
      if gdefault is not None:    # If default value is provided, use it
        new_params[gene_name] = gdefault
      if gene.dtype == bool:      # If gene is boolean, randomly generate True/False
        new_params[gene_name] = np.random.choice([True, False], size=gene.shape)
      else:
        gshape = gene.shape       # Otherwise, uniform generate values in gene range
        gmin = gene.min_val
        gmax = gene.max_val
        gtype = gene.dtype
        new_params[gene_name] = np.random.uniform(low=gmin, high=gmax, size=gshape)
        if gshape is not None:
          new_params[gene_name] = new_params[gene_name].astype(gtype)
        else:
          new_params[gene_name] = gtype(new_params[gene_name])

    return new_params

  # Takes in a Parameters object and mutates it (Note: Returns same Parameters object)
  # Inputs: Parameters
  # Outputs: Parameters (mutated)
  def mutate(self, params: Parameters) -> Parameters:
    for gene_name, gene in self.items():
      gshape = gene.shape
      gtype = gene.dtype
      gmin = gene.min_val
      gmax = gene.max_val
      mut_rate = gene.mutation_rate
      mut_scale = gene.mutation_scale
      if np.random.uniform() < mut_rate:
        if gshape is not None:
          params[gene_name] += np.random.uniform(low=-mut_scale, high=mut_scale, size=gshape).astype(gtype)
        else:
          params[gene_name] += np.random.uniform(low=-mut_scale, high=mut_scale)
        params[gene_name] = np.clip(params[gene_name], gmin, gmax)
    return params

  # Takes in a Parameters object and crosses it with another Parameters object
  # Inputs: list of Parameters (parents)
  # Outputs: Parameters (offspring)
  def crossover(self, parents: list[Parameters], iteration: int) -> Parameters:
    p1, p2 = parents[0], parents[1]  # Only two parents used for now, change later
    child_params = Parameters(iteration=iteration)
    for gene_name, gene in self.items():
      gshape = gene.shape
      p1_gene = p1[gene_name]
      p2_gene = p2[gene_name]
      if gshape is not None:   # If scalar, choose one parent's value
        gshape = p1[gene_name].shape
        full_index = np.prod(gshape)
        splice = np.random.randint(low=0, high=full_index)
        new_param = np.concatenate([p1_gene.flatten()[:splice], p2_gene.flatten()[splice:]])
        child_params[gene_name] = new_param.reshape(gshape)
      else:
        child_params[gene_name] = np.random.choice([p1_gene, p2_gene], p=[0.5, 0.5])

    return child_params


if __name__ == '__main__':
  test = Parameters(0, {'a': np.array([1, 2, 3]), 'b': np.array([4, 5, 6])})
  arr = test.as_array()
  print(arr)
  arr = np.zeros_like(arr)
  test.from_array(arr)
  print(test)