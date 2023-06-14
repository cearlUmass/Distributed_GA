from os.path import join as file_path
import os
import numpy as np
import hashlib
from abc import abstractmethod
from pool_functions import load_gene, write_gene
from ast import literal_eval

POOL_DIR = "pool"
POOL_LOCK_NAME = "POOL_LOCK.lock"


# Return hash of bytes of obj x
def consistent_hasher(x):
  b = bytes(str(x), 'utf-8')
  return hashlib.sha256(b).hexdigest()  # Get the hexadecimal representation of the hash value


# Takes np and transforms into tuple (makes it hashable)
def hashable_nparray(gene: np.array):
  if gene.ndim == 0:  # Scalar value
    return gene.item()
  else:
    return tuple(hashable_nparray(sub_arr) for sub_arr in gene)


def get_pool_key(gene: np.array):
  # np arrays not hashable, convert to tuple
  b = bytes(gene)
  return hashlib.sha256(b).hexdigest()


# Assumed that pool is locked for duration of objects existence
class Algorithm():

  def __init__(self, typing: dict, run_name: str, **kwargs):
    self.run_name = run_name
    self.make_class_vars(typing, **kwargs)
    self.pool_path = file_path(self.run_name, POOL_DIR)
    self.pool = {}

    # Load gene pool
    for root, dirs, files in os.walk(self.pool_path):
      for file in files:
        file_name = file.split('.')[0]    # This will be unique hash of the gene
        gene = load_gene(file_name, self.run_name)
        self.pool[file_name] = gene

  # Behavior: Will add new genes until self.num_genes genes are present. After, new genes
  # created will replace gene with lowest fitness
  @abstractmethod
  def fetch_gene(self, **kwargs):
    pass

  # Take gene and write it to a file. Returns file name and written data
  def create_gene(self, gene: np.array):
    # Generate gene & name
    gene_name = get_pool_key(gene)

    # Write gene to file
    gene_info = {'gene': gene, 'fitness': None, 'status': 'being tested'}
    write_gene(gene_info, gene_name, self.run_name)

    # Return gene/file info
    return gene_name

  # Create class vars with proper typing
  # Note: bash args always returned as strings
  def make_class_vars(self, typing: dict, **kwargs):
    for arg, t in typing.items():
      if t in (bytes, float, int, tuple, list, dict, set, bool):
        arg_value = kwargs[arg]
        if t == type(arg_value):
          setattr(self, arg, arg_value)
        else:
          setattr(self, arg, literal_eval(kwargs[arg]))