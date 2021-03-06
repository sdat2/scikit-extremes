"""
Module containing classical generalistic models

Gumbel:
    To be used applying the Block Maxima approach

Generalised extreme value distribution (GEV):
    To be used applying the Block Maxima approach

Generalised Pareto Distribution (GPD):
    To be used applying the Peak-Over-Threshold approach
    TODO
"""

from collections import OrderedDict

from scipy import stats as _st
from scipy import optimize as _op
from lmoments3 import distr as _lmdistr
import numpy as _np
import matplotlib.pyplot as _plt
import numdifftools as _ndt

from ..utils import bootstrap_ci as _bsci
from ..utils import gev_momfit as _gev_momfit
from ..utils import gum_momfit as _gum_momfit

class _Base:

    def __init__(self, data, ev_unit='',
                 block_unit='', fit_method='mle',
                 ci=0, ci_method=None,
                 return_periods = None,
                 frec=1):
        # Data to be used for the fit
        self.data = data
        self.ev_unit = ev_unit
        self.block_unit = block_unit

        # Fit method to be used
        if fit_method in ['mle', 'mom', 'lmoments']:
            self.fit_method = fit_method
        else:
            raise ValueError(
                ("fit methods accepted are:\n"
                 "    mle (Maximum Likelihood Estimation)\n"
                 "    lmoments\n"
                 "    mom (method of moments)\n")
            )

        # Calculate shape, location, scale and a frozen distribution
        # with the calculated estimators (shape, location, scale)
        self._fit()

        # Check for calculations of return periods and return values.
        self.frec = frec
        if return_periods:
            self.return_periods = _np.array(return_periods)
            self.return_values = self.distr.isf(self.frec /
                                                self.return_periods)
        else:
            self.return_periods = _np.array([])
            self.return_values = _np.array([])

        # Check for the estimation of confidence intervals
        if ci  == 0 or 0 < ci < 1:
            self.ci = ci
        else:
            raise ValueError("ci should be a value in the interval 0 < ci < 1")
        if self.ci:
            if (ci_method and
                fit_method == 'mle' and
                ci_method in ['delta', 'bootstrap']):
                self.ci_method = ci_method
                self._ci()
            elif (ci_method and
                fit_method == 'lmoments' and
                ci_method in ['bootstrap']):
                self.ci_method = ci_method
                self._ci()
            elif (ci_method and
                fit_method == 'mom' and
                ci_method in ['bootstrap']):
                self.ci_method = ci_method
                self._ci()
            else:
                raise ValueError(
                ("You should provide a valid value for the confidence\n"
                 "interval calculation, 'ci_method'\n"))


    def _fit(self):
        # This is a base class and shouldn't be used as it.
        # This method should be implemented in the subclass.
        raise NotImplementedError("Subclasses should implement this!")

    def _ci(self):
        # This is a base class and shouldn't be used 'as is'.
        # This method should be implemented in the subclass.
        raise NotImplementedError("Subclasses should implement this!")

    def pdf(self, quantiles):
        # A shortcut to the frozen distribution pdf as provided by scipy.
        """
        Probability density function at x of the given frozen RV.

        **Parameters**

        x : array_like
            quantiles

        **Returns**

        pdf : ndarray
            Probability density function evaluated at x
        """

        return self.distr.pdf(quantiles)

    def cdf(self, quantiles):
        # A shortcut to the frozen distribution cdf as provided by scipy.
        """
        Cumulative distribution function of the given frozen RV.

        **Parameters**

        x : array_like
            quantiles

        **Returns**

        cdf : ndarray
            Cumulative distribution function evaluated at `x`
        """

        return self.distr.cdf(quantiles)

    def ppf(self, q):
        # A shortcut to the frozen distribution ppf as provided by scipy.
        """
        Percent point function (inverse of cdf) at q of the given frozen RV.

        **Parameters**

        q : array_like
            lower tail probability

        **Returns**

        x : array_like
            quantile corresponding to the lower tail probability q.
        """

        return self.distr.ppf(q)

    def stats(self, moments):
        # A shortcut to the frozen distribution stats as provided by scipy.
        """
        Some statistics of the given RV.

        **Parameters**

        moments : str, optional
            composed of letters ['mvsk'] defining which moments to compute:
            'm' = mean,
            'v' = variance,
            's' = (Fisher's) skew,
            'k' = (Fisher's) kurtosis.
            (default='mv')

        **Returns**

        stats : sequence
            of requested moments.
        """

        return self.distr.stats(moments)

    def _plot(self, ax, title, xlabel, ylabel):
        # helper function for:
        #     self.plot_density()
        #     self.plot_pp()
        #     self.plot_qq()
        #     self.plot_return_values()
        #     self.plot_summary()
        # ax.set_facecolor((0.95, 0.95, 0.95))
        _plt.setp(ax.lines, linewidth=1, color='#CB4154')
        ax.set_title(title)
        ax.set_xlabel(xlabel)
        ax.set_ylabel(ylabel)
        ax.grid(True)
        return ax

    def plot_density(self):
        """
        Histogram of the empirical pdf data and the pdf plot of the
        fitted distribution. All parameters are predefined from the
        frozen fitted model and empirical data available.

        **Returns**

        Density plot.
        """

        fig, ax = _plt.subplots(figsize=(8, 6))

        # data
        x = _np.linspace(self.distr.ppf(0.001), self.distr.ppf(0.999), 100)

        # plot
        ax.plot(x, self.distr.pdf(x), label='Fitted', color='k')
        ax.hist(self.data, density=True,
                color='#a3c1ad', alpha=0.75,
                label="Empirical")
        ax = self._plot(ax, 'Density Plot', '$x$ '+self.ev_unit, 'f($x$)')
        ax.legend(loc='best', frameon=False)

    def plot_pp(self):
        """
        PP (probability) plot between empirical and fitted data.
        All parameters are predefined from the frozen fitted model and empirical
        data available.

        **Returns**

        PP plot.
        """

        fig, ax = _plt.subplots(figsize=(8, 6))

        # data
        data = _np.sort(self.data)
        N = len(data)
        y = _np.arange(1, N + 1) / (N + 1)
        x = self.distr.cdf(data)

        # plot
        ax.scatter(x, y, marker='+', color='darkcyan')
        ax.plot([0, 1], [0, 1])
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax = self._plot(ax, 'P-P Plot', 'Model', 'Empirical')

    def plot_qq(self):
        """
        QQ (Quantile-Quantile) plot between empirical and fitted data.
        All parameters are predefined from the frozen fitted model and empirical
        data available.

        **Returns**

        QQ plot.
        """

        fig, ax = _plt.subplots(figsize=(8, 6))

        # data
        y = _np.sort(self.data)
        N = len(y)
        x = _np.arange(1, N + 1) / (N + 1)
        x = self.distr.ppf(x)

        # plot
        ax = self._plot(ax, 'Q-Q Plot', 'Model', 'Empirical')
        ax.scatter(x, y, marker='+',
                   color='#002147', alpha=0.7)
        low_lim = _np.min([x, y]) * 0.95
        high_lim = _np.max([x, y]) * 1.05
        ax.plot([low_lim, high_lim], [low_lim, high_lim], marker='+', c='k')
        ax.set_xlim(low_lim, high_lim)
        ax.set_ylim(low_lim, high_lim)

    def plot_return_values(self):
        """
        Return values and return periods of data. If confidence interval
        information has been provided it will show the confidence interval
        values.

        **Returns**

        Return values and return periods plot.
        """

        fig, ax = _plt.subplots(figsize=(8, 6))

        # data
        T = _np.arange(0.1, 500.1, 0.1)
        # the time sampled linearly
        sT = self.distr.isf(self.frec * 1./T)
        # the inverse survival function
        N = _np.r_[1:len(self.data)+1] * self.frec
        # unclear -- some numpy magic?
        Nmax = max(N)

        # plot

        ax = self._plot(ax, 'Return Level Plot',
                        'Return period', 'Return level')
        # ok semilogx apparently gets the settings right for the next
        # plot too.
        ax.semilogx(T, sT, 'k', color='#CB4154')
        ax.scatter(self.frec * Nmax/N, sorted(self.data)[::-1],
                    color='#002147', alpha=0.7)
        # plot confidence intervals if available
        if self.ci:
            #y1 = sT - st.norm.ppf(1 - self.ci / 2) * np.sqrt(self._ci_se)
            #y2 = sT + st.norm.ppf(1 - self.ci / 2) * np.sqrt(self._ci_se)
            # thanks to the delta error theory, the errors are Gaussian in
            # this space.
            ax.semilogx(T, self._ci_Td, '--',
                         color='#CB4154', alpha=0.6)
            ax.semilogx(T, self._ci_Tu, '--',
                         color='#CB4154', alpha=0.6)
            ax.fill_between(T, self._ci_Td, self._ci_Tu,
                             color='#a3c1ad', alpha=0.25)
            ax.set_xlim([0.8, _np.max(T)])


    def plot_summary(self):
        """
        Summary plot including PP plot, QQ plot, empirical and fitted pdf and
        return values and periods.

        **Returns**

        4-panel plot including PP, QQ, pdf and return level plots
        """

        # These are in a bizzare order.

        fig, ((ax3, ax2), (ax4, ax1)) = _plt.subplots(2, 2, figsize=(8, 6))

        # PDF plot
        x = _np.linspace(self.distr.ppf(0.001),
                         self.distr.ppf(0.999),
                         100)
        ax1.plot(x, self.distr.pdf(x), label='Fitted')
        ax1.hist(self.data, density=True,
                 color='#a3c1ad', alpha=0.75, label="Empirical")
        ax1 = self._plot(ax1, 'Density Plot',
                         '$x$'+ self.ev_unit, 'f($x$)')
        ax1.legend(loc='best', frameon=False)

        # QQ plot
        data = _np.sort(self.data)
        N = len(data)
        y = _np.arange(1, N + 1) / (N + 1)
        x = self.distr.cdf(data)
        ax2.plot([0, 1], [0, 1])
        ax2.set_xlim(0, 1)
        ax2.set_ylim(0, 1)
        ax2 = self._plot(ax2, 'P-P Plot', 'Model', 'Empirical')
        ax2.scatter(x, y, marker='+', color='#002147', alpha=0.7)

        # PP Plot
        y = _np.sort(self.data)
        N = len(y)
        x = _np.arange(1, N + 1) / (N + 1)
        x = self.distr.ppf(x)
        ax3.scatter(x, y, color='#002147', alpha=0.7)
        low_lim = _np.min([x, y]) * 0.95
        high_lim = _np.max([x, y]) * 1.05
        ax3.plot([low_lim, high_lim], [low_lim, high_lim])
        ax3.set_xlim(low_lim, high_lim)
        ax3.set_ylim(low_lim, high_lim)
        ax3 = self._plot(ax3, 'Q-Q Plot', 'Model', 'Empirical')

        # Return levels plot
        T = _np.arange(0.1, 500.1, 0.1)
        sT = self.distr.isf(self.frec/T)
        # In other words start:stop:stepj is interpreted as np.linspace(start, stop, step, endpoint=1)
        N = _np.r_[1:len(self.data)+1] * self.frec
        # https://docs.scipy.org/doc/numpy/reference/generated/numpy.r_.html
        # translates a slice object into concatenation along the first axis
        #  In other words start:stop:stepj is interpreted as np.linspace(start, stop, step, endpoint=1)
        # so I think thsi is equivalent to [1, 2, 3]*self.freq
        # where frec is really the time period.
        # This repository is v. confusing.

        Nmax = max(N)
        ax4 = self._plot(ax4,
                         'Return Level Plot',
                         'Return Period ' + self.block_unit,
                         'Return Level' + self.ev_unit)
        ax4.semilogx(T, sT, 'k', color='#CB4154')
        ax4.scatter(self.frec * Nmax/N, # this is the second time timesing through by
                    sorted(self.data)[::-1],
                    color='#002147', alpha=0.7)


        if self.ci:
            #y1 = sT - st.norm.ppf(1 - self.ci / 2) * np.sqrt(self._ci_se)
            #y2 = sT + st.norm.ppf(1 - self.ci / 2) * np.sqrt(self._ci_se)
            ax4.semilogx(T, self._ci_Td, '--',
                         color='#CB4154', alpha=0.6)
            ax4.semilogx(T, self._ci_Tu, '--',
                         color='#CB4154', alpha=0.6)
            ax4.fill_between(T, self._ci_Td, self._ci_Tu,
                             color='#a3c1ad', alpha=0.25)
            ax4.set_xlim([0.8, _np.max(T)])

        # I love matplotlib for stuff like this, thanks, guys!!!
        _plt.tight_layout()

        return fig, ax1, ax2, ax3, ax4

    def plot_pi_gp(self, tend_from, tend_to, plateau_by):
        import numpy as np
        from sklearn.gaussian_process import GaussianProcessRegressor
        from sklearn.gaussian_process.kernels import RBF, WhiteKernel
        kernel = (1* RBF(length_scale=30,
                        length_scale_bounds=(5, 50),# periodicity=8000
                        ) + 1.0 * WhiteKernel(noise_level=1e-1))


        T = _np.arange(0.1, 500.1, 0.1)
        # sT = self.distr.isf(self.frec/T)
        # In other words start:stop:stepj is interpreted as np.linspace(start, stop, step, endpoint=1)

        # @vectorise
        def _func(values):
            offset = np.zeros(len(values) )
            for i in range(len(values)):
                if values[i]-1 < plateau_by and values[i]-1 > 0:
                    offset[i] = values[i] / plateau_by * (tend_to-tend_from) + tend_from
                elif values[i]-1 >= plateau_by:
                    offset[i] = tend_to
                else:
                    offset[i] = tend_from

            return offset

        N = _np.r_[1:len(self.data)+1] * self.frec
        Nmax = max(N)
        x_values = self.frec * Nmax/N
        y_values = sorted(self.data)[::-1]
        x_values_gp = np.asarray(x_values).reshape(-1, 1)
        y_values_gp = np.asarray(y_values-_func(x_values)).reshape(-1, 1)
        x_pred_npa = T.reshape(-1, 1)

        print('x_values', x_values)
        print('shape', np.shape(x_values))
        print('y_values', y_values)
        print('shape', np.shape(y_values))

        assert(np.shape(y_values) == np.shape(x_values))

        gp_object = GaussianProcessRegressor(kernel=kernel, alpha=0.005).fit(x_values_gp, y_values_gp)

        y_pred_npa, y_cov = gp_object.predict(x_pred_npa, return_cov=True)

        y_pred_npa = y_pred_npa.ravel() + _func(x_pred_npa.ravel() )


        fig, ax = _plt.subplots(figsize=(8, 6))

        ax = self._plot(ax, 'Return Level Plot - w. GP fit.',
                        'Return period (Yrs)', 'Return level (m)')
        # ok semilogx apparently gets the settings right for the next
        # plot too.
        ax.set_xscale('log')
        ax.scatter(x_values, y_values,
                    color='#002147', alpha=0.7)

        # plot the Gaussian process.

        ax.plot(x_pred_npa.ravel(),
                y_pred_npa.ravel(),
                '#002147',
                lw=1,
                zorder=9,
                alpha=0.7,
                label='GP Prediction')

        for sig_mult, alpha in [[1, 0.4], [2, 0.2]]: #, [3, 0.1], [4, 0.1]]:
            # This is the strength of the shading at each value of sigma
            ax.fill_between(x_pred_npa.ravel(), y_pred_npa.ravel() - sig_mult*np.sqrt(np.diag(y_cov)).ravel(),
                            (y_pred_npa).ravel() + sig_mult*np.sqrt(np.diag(y_cov)).ravel(),
                            alpha=alpha, color='#a3c1ad', label='%s $\sigma$ envelope' % str(sig_mult))

        ax.set_xlim([0.8, _np.max(T)])


class GEV(_Base):
    """
    Class to fit data to a Generalised extreme value (GEV) distribution.

    **Parameters**

    data : array_like
        1D array_like with the extreme values to be considered
    fit_method : str
        String indicating the method used to fit the distribution.
        Availalable values are 'mle' (default value), 'mom' and 'lmoments'.
    ci : float (optional)
        Float indicating the value to be used for the calculation of the
        confidence interval. The returned values are (ci/2, 1-ci/2)
        percentile confidence intervals. E.g., a value of 0.05 will
        return confidence intervals at 0.025 and 0.975 percentiles.
    ci_method : str (optional)
        String indicating the method to be used to calculate the
        confidence intervals. If ``ci`` is not supplied this parameter will
        be ignored. Possible values depend of the fit method chosen. If
        the fit method is 'mle' possible values for ci_method are
        'delta' and 'bootstrap', if the fit method is 'mom' or
        'lmoments' possible value for ci_method is 'bootstrap'.
            'delta' is for delta method.
            'bootstrap' is for parametric bootstrap.
    return_period : array_like (optional)
        1D array_like of values for the *return period*. Values indicate
        **years**.
    frec : int or float
        Value indicating the frecuency of events per year. If frec is
        not provided the data will be treated as yearly data (1 value per
        year).

    **Attributes and Methods**

    params : OrderedDict
        Ordered dictionary with the values of the *shape*, *location* and
        *scale* parameters of the distribution.
    c : flt
        Float value for the *shape* parameter of the distribution.
    loc : flt
        Float value for the *location* parameter of the distribution.
    scale : flt
        Float value for the *scale* parameter of the distribution.
    distr : object
        Frozen RV object with the same methods of a continuous scipy
        distribution but holding the given *shape*, *location*, and *scale*
        fixed. See http://docs.scipy.org/doc/scipy/reference/stats.html
        for more info.
    data : array_like
        Input data used for the fit
    fit_method : str
        String indicating the method used to fit the distribution,
        values can be 'mle', 'mom' or 'lmoments'.
    """

    def _fit(self):

        # Fit can be made using Maximum Likelihood Estimation (mle) or using
        # l-moments.
        # L-moments is fast and accurate most of the time for the GEV
        # distribution.

        # MLE FIT
        # In the case of the mle estimation, sometimes we get unstable values
        # if we don't provide an initial guess of the parameters. Loc and scale
        # are more or less stable but shape can be quite unstable depending the
        # input data. This is why we are using lmoments to obtain start values
        # for the mle optimization. For mle we are using fmin_bfgs as it is
        # faster than others and with the first guess provide accurate results.

        if self.fit_method == 'mle':

            # Initial guess to make the fit of GEV more stable
            # To do the initial guess we are using lmoments...

            _params0 = _lmdistr.gev.lmom_fit(self.data)
            # The mle fit will start with the initial estimators obtained
            # with lmoments above

            _params = _st.genextreme.fit(self.data, _params0['c'],
                                         loc = _params0['loc'],
                                         scale = _params0['scale'],
                                         optimizer = _op.fmin_bfgs)

            self.params = OrderedDict()
            # For the shape parameter the value provided by scipy
            # is defined as negative as that obtained from other
            # packages in R, some textbooks, wikipedia,... ¿?
            self.params["shape"]    = _params[0]
            self.params["location"] = _params[1]
            self.params["scale"]    = _params[2]

        # L-MOMENTS FIT
        if self.fit_method == 'lmoments':

            _params = _lmdistr.gev.lmom_fit(self.data)
            self.params = OrderedDict()
            # For the shape parameter the value provided by lmoments3
            # is defined as negative as that obtained from other
            # packages in R, some textbooks, wikipedia,... ¿?
            self.params["shape"]    = _params['c']
            self.params["location"] = _params['loc']
            self.params["scale"]    = _params['scale']

        # METHOD OF MOMENTS FIT
        if self.fit_method == 'mom':

            _params = _gev_momfit(self.data)
            self.params = OrderedDict()
            self.params["shape"]    = _params[0]
            self.params["location"] = _params[1]
            self.params["scale"]    = _params[2]

        # Estimators and a frozen distribution for the estimators
        self.c     = self.params['shape']      # shape
        self.loc   = self.params['location']   # location
        self.scale = self.params['scale']      # scale
        self.distr = _st.genextreme(self.c,     # frozen distribution
                                    loc = self.loc,
                                    scale = self.scale)
        # self.distr is a scipy.stats.genextreme obj.


    def _nnlf(self, theta):
        # This is used to calculate the variance-covariance matrix using the
        # Hessian from numdifftools
        # see self._ci_delta() method below

        x = self.data

        # Here we provide code for the GEV distribution and for the special
        # case when shape parameter is 0 (Gumbel distribution).
        if len(theta) == 3:
            c = theta[0]
            loc = theta[1]
            scale = theta[2]
        if len(theta) == 2:
            c = 0
            loc = theta[0]
            scale = theta[1]
        if c != 0:
            expr = 1. + c * ((x - loc) / scale)
            return (len(x) * _np.log(scale) +
                    (1. + 1. / c) * _np.sum(_np.log(expr)) +
                    _np.sum(expr ** ( -1. / c)))
        else:
            expr = (x - loc) / scale
            return (len(x) * _np.log(scale) +
                    _np.sum(expr) +
                    _np.sum(_np.exp( -expr)))

    def _ci_delta(self):
        # Calculate the variance-covariance matrix using the
        # hessian from numdifftools
        # This is used to obtain confidence intervals for the estimators and
        # the return values for several return values.
        #
        # More info about the delta method can be found on:
        #     - Coles, Stuart: "An Introduction to Statistical Modeling of
        #     Extreme Values", Springer (2001)
        #     - https://en.wikipedia.org/wiki/Delta_method

        # data
        c  = -self.c    # We negate the shape to avoid inconsistency problems!?
        # I.e we have just swapped the sign convention for the shape parameter!
        # This is very confusing, please don't copy down the wrong maths.

        loc = self.loc # at least these two parameters don't change sign.
        scale = self.scale

        hess = _ndt.Hessian(self._nnlf)  # https://en.wikipedia.org/wiki/Hessian_matrix
        T = _np.arange(0.1, 500.1, 0.1) # years chosen from  0.1 to 500.1 in linear space
        sT = -_np.log(1. - self.frec / T) # ~~return period
        sT2 = self.distr.isf(self.frec / T)

        # the inverse survival function
        # The size of the extreme value (I think)?
        # Actually the precent pint fucntion which gives the probability
        # https://www.itl.nist.gov/div898/handbook/eda/section3/eda362.htm
        # It goes from the largest to the smallest value.
        # Z(α)=G(1−α)
        # The horizontal axis is the probability.
        # The Y axis fed out is the extreme value.

        # VarCovar matrix and confidence values for estimators and return values
        # Confidence interval for return values (up values and down values)
        # automatically have zeros (would NaNs be better?). This might fail too quietly.
        ci_Tu = _np.zeros(sT.shape)
        ci_Td = _np.zeros(sT.shape)

        # I currently don't understand the truth value of a float.

        if c:
            # sign convention still reversed!!!

            print('\n c is ', c, '\n')

            # If c then we are calculating GEV confidence intervals
            print('\n !working out GEV confidence intervals! \n')

            varcovar = _np.linalg.inv(hess([c, loc, scale])) # wow.
            self.params_ci = OrderedDict()
            se = _np.sqrt(_np.diag(varcovar))
            self._se = se

            # symmetric error bars in all the parameters.
            # sign convention not reversed!!!

            self.params_ci['shape']    = (self.c - _st.norm.ppf(1 - self.ci / 2) * se[0],
                                          self.c + _st.norm.ppf(1 - self.ci / 2) * se[0])
            self.params_ci['location'] = (self.loc - _st.norm.ppf(1 - self.ci / 2) * se[1],
                                          self.loc + _st.norm.ppf(1 - self.ci / 2) * se[1])
            self.params_ci['scale']    = (self.scale - _st.norm.ppf(1 - self.ci / 2) * se[2],
                                          self.scale + _st.norm.ppf(1 - self.ci / 2) * se[2])

            for i, val in enumerate(sT2):
                # sign convention still reversed!!!



                gradZ = [(scale * (c**(-2)) * (1 - (sT[i] ** (-c)))
                          - scale * (c**(-1)) * (sT[i]**-c) * _np.log(sT[i])),
                         1,
                         - (1 - sT[i] ** (-c)) / c]

                se = _np.dot(_np.dot(gradZ, varcovar), _np.array(gradZ).T)

                # Gosh, what did that line do?
                ci_Tu[i] = val + _st.norm.ppf(1 - self.ci / 2) * _np.sqrt(se) # upper limit.
                ci_Td[i] = val - _st.norm.ppf(1 - self.ci / 2) * _np.sqrt(se) # lower limit.
                # sign convention still reversed!!!


        else:
            # else then we are calculating Gumbel confidence intervals.
            print('\n !!!GUMBEL confidence intervals being calculated!!! \n')
            varcovar = _np.linalg.inv(hess([loc, scale]))
            self.params_ci = OrderedDict()
            se = _np.sqrt(_np.diag(varcovar))
            self._se = se

            self.params_ci['shape']    = (0, 0)
            self.params_ci['location'] = (self.loc - _st.norm.ppf(1 - self.ci / 2) * se[0],
                                          self.loc + _st.norm.ppf(1 - self.ci / 2) * se[0])
            self.params_ci['scale']    = (self.scale - _st.norm.ppf(1 - self.ci / 2) * se[1],
                                          self.scale + _st.norm.ppf(1 - self.ci / 2) * se[1])

            for i, val in enumerate(sT2):
                gradZ = [1, -_np.log(sT[i])]
                se = _np.dot(_np.dot(gradZ, varcovar), _np.array(gradZ).T)
                ci_Tu[i] = val + _st.norm.ppf(1 - self.ci / 2) * _np.sqrt(se)
                ci_Td[i] = val - _st.norm.ppf(1 - self.ci / 2) * _np.sqrt(se)

        self._ci_Tu = ci_Tu
        self._ci_Td = ci_Td

    def _ci_bootstrap(self):
        # Calculate confidence intervals using parametric bootstrap and the
        # percentil interval method
        # This is used to obtain confidence intervals for the estimators and
        # the return values for several return values.
        # all the code in skextremes.utils.bootstrap_ci has been adapted and
        # simplified from that on https://github.com/cgevans/scikits-bootstrap.
        #
        # More info about bootstrapping can be found on:
        #     - https://github.com/cgevans/scikits-bootstrap
        #     - Efron: "An Introduction to the Bootstrap", Chapman & Hall (1993)
        #     - https://en.wikipedia.org/wiki/Bootstrapping_%28statistics%29

        # parametric bootstrap for return levels and parameters

        # The function to bootstrap
        def func(data):
            sample = _st.genextreme.rvs(self.c,
                                        loc=self.loc,
                                        scale=self.scale,
                                        size=len(self.data))
            c, loc, scale = _st.genextreme.fit(sample, self.c,
                                               loc=self.loc,
                                               scale=self.scale,
                                               optimizer=_op.fmin_bfgs)

            T = _np.arange(0.1, 500.1, 0.1)
            sT = _st.genextreme.isf(self.frec/T, c, loc=loc, scale=scale)
            res = [c, loc, scale]
            res.extend(sT.tolist())
            return tuple(res)

        # the calculations itself
        out = _bsci(self.data, statfunction=func, n_samples=500)
        self._ci_Td = out[0, 3:]
        self._ci_Tu = out[1, 3:]
        self.params_ci = OrderedDict()
        self.params_ci['shape']    = (out[0,0], out[1,0])
        self.params_ci['location'] = (out[0,1], out[1,1])
        self.params_ci['scale']    = (out[0,2], out[1,3])

    def _ci(self):
        # Method called internally to calculate confidence intervals if
        # required. To see more info about available methods see comments on
        # self._ci_delta and self._ci_bootstrap methods.

        if self.ci_method == "delta":
            self._ci_delta()
        if self.ci_method == "bootstrap":
            self._ci_bootstrap()

class Gumbel(GEV):
    __doc__ = GEV.__doc__.replace("Generalised extreme value (GEV) distribution.",
                                  ("Gumbel distribution. Note that this is a "
                                   "special case of the ``GEV`` class where "
                                   "the 'shape' is fixed to 0."))

    def _fit(self):

        if self.fit_method == 'mle':
            _params = _st.gumbel_r.fit(self.data)
            self.params = OrderedDict()
            self.params["shape"]    = 0
            self.params["location"] = _params[0]
            self.params["scale"]    = _params[1]

        if self.fit_method == 'lmoments':
            _params = _lmdistr.gum.lmom_fit(self.data)
            self.params = OrderedDict()
            self.params["shape"]    = 0
            self.params["location"] = _params['loc']
            self.params["scale"]    = _params['scale']

        # METHOD OF MOMENTS FIT
        if self.fit_method == 'mom':
            _params = _gum_momfit(self.data)
            self.params = OrderedDict()
            self.params["shape"]    = _params[0]
            self.params["location"] = _params[1]
            self.params["scale"]    = _params[2]

        self.c     = self.params['shape']
        self.loc   = self.params['location']
        self.scale = self.params['scale']
        self.distr = _st.gumbel_r(loc=self.loc,
                                  scale=self.scale)

class GPD(_Base):
    pass
