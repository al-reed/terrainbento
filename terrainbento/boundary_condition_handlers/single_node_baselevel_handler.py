#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""``SingleNodeBaselevelHandler`` changes elevation for a single boundary node."""
import os
import numpy as np
from scipy.interpolate import interp1d

from landlab import Component

class SingleNodeBaselevelHandler(Component):
    """Control the elevation of a single open boundary node.

    The ``SingleNodeBaselevelHandler`` controls the elevation of a single open
    boundary node, referred to here as the *outlet*. The outlet lowering rate is
    specified either as a constant or through a time or through a textfile that
    specifies the elevation change through time.

    The ``SingleNodeBaselevelHandler`` expects that ``topographic__elevation``
    is a at-node model grid field. It will modify this field and, if it exists,
    the field ``bedrock__elevation``.

    Note that ``SingleNodeBaselevelHandler`` increments time at the end of the
    ``run_one_step`` method.

    Methods
    -------
    run_one_step

    """

    def __init__(self,
                 grid,
                 outlet_node,
                 lowering_rate = None,
                 lowering_file_path = None,
                 model_end_elevation = None,
                 **kwargs):
        """
        Parameters
        ----------
        grid : landlab model grid
        outlet_node : int
            Node ID of the outlet node.
        lowering_rate : float, optional
            Lowering rate of the outlet node. One of ``lowering_rate`` and
            ``lowering_file_path`` is required. Units are implied by the
            model grids spatial scale and the time units of ``dt``. Negative
            values mean that the outlet lowers.
        lowering_file_path : str, optional
            Lowering lowering history file path. One of ``lowering_rate``
            and ``lowering_file_path`` is required. Units are implied by
            the model grids spatial scale and the time units of ``dt``.
            This file should be readable with
            ``np.loadtxt(filename, skiprows=1, delimiter=',')``
            Its first column is time and its second column is the elevation
            change at the outlet since the onset of the model run. Negative
            values mean the outlet lowers.
        model_end_elevation : float, optional
            Elevation of the outlet at the end of the model run duration. When
            the outlet is lowered based on a lowering_file_path, a
            ``model_end_elevation`` can be set such that lowering is scaled
            based on the starting and ending outlet elevation. Default behavior
            is to not scale the lowering pattern.

        Examples
        --------
        Start by creating a landlab model grid.

        >>> from landlab import RasterModelGrid
        >>> mg = RasterModelGrid(5, 5)
        >>> z = mg.add_zeros('node', 'topographic__elevation')
        >>> print(z.reshape(mg.shape))
        [[ 0.  0.  0.  0.  0.]
         [ 0.  0.  0.  0.  0.]
         [ 0.  0.  0.  0.  0.]
         [ 0.  0.  0.  0.  0.]
         [ 0.  0.  0.  0.  0.]]

        Now import the ``SingleNodeBaselevelHandler`` and instantiate.

        >>> from terrainbento.boundary_condition_handlers import (
        ...                                         SingleNodeBaselevelHandler)
        >>> bh = SingleNodeBaselevelHandler(mg,
        ...                                 outlet_node = 0,
        ...                                 lowering_rate = -0.1)
        >>> bh.run_one_step(10.0)

        We should expect that node 0 has lowered by one, to an elevation of -1.

        >>> print(z.reshape(mg.shape))
        [[-1.  0.  0.  0.  0.]
         [ 0.  0.  0.  0.  0.]
         [ 0.  0.  0.  0.  0.]
         [ 0.  0.  0.  0.  0.]
         [ 0.  0.  0.  0.  0.]]

        More complex baselevel histories can be provided with a
        ``lowering_file_path``.

        """
        super(SingleNodeBaselevelHandler, self).__init__(grid)

        self.model_time = 0.0
        self._grid = grid
        self.outlet_node = outlet_node
        self.z = self._grid.at_node['topographic__elevation']

        if (lowering_file_path is None) and (lowering_rate is None):
            raise ValueError(('SingleNodeBaselevelHandler requires one of '
                              'lowering_rate and lowering_file_path'))
        else:
            if (lowering_rate is None):
                # initialize outlet elevation object
                if os.path.exists(lowering_file_path):

                    model_start_elevation = self.z[self.outlet_node]
                    elev_change_df = np.loadtxt(lowering_file_path, skiprows=1, delimiter =',')
                    time = elev_change_df[:, 0]
                    elev_change = elev_change_df[:, 1]

                    if model_end_elevation is None:
                        scaling_factor = 1.0
                    else:
                        scaling_factor = np.abs(model_start_elevation-model_end_elevation)/np.abs(elev_change[0]-elev_change[-1])
                    outlet_elevation = (scaling_factor*elev_change_df[:, 1]) + model_start_elevation
                    self.outlet_elevation_obj = interp1d(time, outlet_elevation)
                    self.lowering_rate = None
                else:
                    raise ValueError(('The lowering_file_path provided '
                                      'to SingleNodeBaselevelHandler does not '
                                      'exist.'))
            elif (lowering_file_path is None):
                self.lowering_rate = lowering_rate
                self.outlet_elevation_obj = None
            else:
                raise ValueError(('Both an lowering_rate and a '
                                  'lowering_file_path have been provided '
                                  'to SingleNodeBaselevelHandler. Please provide '
                                  'only one.'))

    def run_one_step(self, dt):
        """ Run ``SingleNodeBaselevelHandler`` to update outlet node elevation.

        The ``run_one_step`` method provides a consistent interface to update
        the ``terrainbento`` boundary condition handlers.

        In the ``run_one_step`` routine, the ``SingleNodeBaselevelHandler``
        will change the elevation of the outlet node based on inputs specified
        at instantiation.

        Note that ``SingleNodeBaselevelHandler`` increments time at the end of
        the ``run_one_step`` method.

        Parameters
        ----------
        dt : float
            Duration of model time to advance forward.
        """
        # first, if we do not have an outlet elevation object
        if self.outlet_elevation_obj is None:

            # calculate lowering amount and subtract
            self.z[self.outlet_node] += self.lowering_rate * dt

            # if bedrock__elevation exists as a field, lower it also
            if 'bedrock__elevation' in self._grid.at_node:
                self._grid.at_node['bedrock__elevation'][self.outlet_node] += self.lowering_rate * dt

        # if there is an outlet elevation object
        else:
            # if bedrock__elevation exists as a field, lower it also
            # calcuate the topographic change required to match the current time's value for
            # outlet elevation. This must be done in case bedrock elevation exists, and must
            # be done before the topography is lowered
            topo_change = self.z[self.outlet_node] - self.outlet_elevation_obj(self.model_time)

            if 'bedrock__elevation' in self._grid.at_node:
                self._grid.at_node['bedrock__elevation'][self.outlet_node] -= topo_change

            # lower topography
            self.z[self.outlet_node] -= topo_change
        # increment model time
        self.model_time += dt
