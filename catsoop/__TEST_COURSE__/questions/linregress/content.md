<python>
cs_content_header = cs_long_name

ys = [-26.85901649618508, -4.82309989277328, 358.12325659886665, -236.27303224345013, 78.96311735375048, -122.0718747926675, -91.794917932851, 156.92288603409375, 77.76372162876706, 134.08018802466293, 421.2164012311623, -102.44084767789477, 69.05193026508634, -65.1707634424306, -6.811873517536455, 14.464555720475445, 123.35092804160584, 269.2411300965563, 283.6126314082743, 249.5593597768601, -45.93699758535121, 160.9929838505804, -11.486651027732734, 34.89429129194224, 227.0114874496006, 453.94991714737176, 159.59340132582852, 305.53172734934645, 209.30183669664237, 377.794764790121, 316.6853125571703, 242.97813270158048, 99.55136064457564, 380.8281222370041, 517.9678491133832, 152.82974416562115, 501.3107247844115, 385.00869117981006, 260.76894288405657, 245.62085551544348, 381.93212971867905, 282.37383569434684, 255.6684633511091, 528.9665009201663, 214.89786230001818, 198.47447067627894, 583.0632870160896, 556.0811185746013, 334.2809525610168, 743.3044708948721, 279.7165711058779, 755.3224521456882, 200.5387369220224, 138.47687852393108, 197.63575541409483, 181.71767331525095, 376.89074479245284, 652.3613138217629, 381.4275586382469, 476.0995327254289, 461.46417474466193, 423.8593541888392, 503.3792036069044, 567.7438934709394, 296.9627154414269, 183.36747560528335, 714.4663522847009, 620.296512084993, 315.16553989225656, 644.953867681399, 381.11694172321086, 392.7101550383068, 474.0136908544534, 556.91031778183, 625.6146302263054, 561.5239749404492, 491.3389262641957, 396.09862792366937, 328.9611909946891, 442.51020674282574, 637.3002734137215, 820.1180066579375, 704.0222105099904, 749.7416740127572, 571.3375044210943, 740.3732575510189, 508.23757383850227, 805.9057544835931, 652.1781007402574, 331.2078936574819, 659.394649695742, 779.5249873375656, 417.1728951942524, 727.5381994766699, 846.8237700909708, 372.6078315611338, 735.4394177096567, 359.3157568184622, 742.5223675039202, 645.445434892132]
xs = [103+i for i in range(len(ys))]

import matplotlib
matplotlib.use('Agg')

import matplotlib.pyplot as plt
from io import BytesIO

def sample_mean(xs):
    return sum(xs) / len(xs)

def sample_stddev(xs):
    m = sample_mean(xs)
    return (sum([(i-m)**2 for i in xs]) / (len(xs)-1))**0.5

def sample_cov(xs, ys):
    x_mean = sample_mean(xs)
    y_mean = sample_mean(ys)
    o = 0.0
    for index in range(len(xs)):
        o += (xs[index] - x_mean)*(ys[index] - y_mean)
    return o / (len(xs) - 1)

def pearson_r(xs, ys):
    return sample_cov(xs, ys) / (sample_stddev(xs)*sample_stddev(ys))

def lin_regress_2(xs, ys):
    r = pearson_r(xs, ys)
    m = r * sample_stddev(ys) / sample_stddev(xs)
    b = sample_mean(ys) - m * sample_mean(xs)
    return m, b, r

m, b, r = lin_regress_2(xs, ys)

import base64

def make_regress_plot(data_x, data_y, m, b):
    fig = plt.figure()
    plt.scatter(data_x, data_y)
    plt.plot([min(data_x), max(data_x)], [m*min(data_x)+b, m*max(data_x)+b], 'r')
    x = savefig()
    return x

def savefig():
    b = BytesIO()
    plt.savefig(b)
    return '<img style="width:400px" src="data:image/png;base64,%s" />' % base64.b64encode(b.getvalue()).decode()

fig = plt.figure()
plt.scatter(xs, ys)
img1 = savefig()
</python>

<center><a href="https://www.youtube.com/watch?v=8qjl4lysi_s" target="_blank">Music for this Problem</a></center>

<section>Introduction</section>

In this exercise, we will write a program to compute a 2-dimensional _linear
regression_ for a set of data.  In short, we will try to explain the
relationship between an independent variable $X$ and a single dependent
variable $Y$ based on a set of $N$ experimental data points $[(x_0, y_0), (x_1,
y_1), \ldots, (x_{N-1}, y_{N-1})]$.

In particular, we will try to find the line $y = mx + b$ that best approximates
the relationship represented in the data.  In addition, we will calculate
[Pearson's r](https://en.wikipedia.org/wiki/Pearson_correlation_coefficient)
for the variables, which will tell us how strongly the two variables are
correlated.

Here, we will consider the "best fit" line to be the one that minimizes the sum
of squared errors between the sampled $y$ values and the values predicted by
the line:

$$\underset{m, b}{\text{argmin}} \sum_{i=0}^{N-1}\left(y_i - (mx_i + b)\right)^2$$

For example, here is a set of data:

<center>
@{img1}
</center>

And here is the line that best approximates the relationship between the two variables:

<center>
@{make_regress_plot(xs, ys, m, b)}
</center>

Next week, we will look at _using_ linear regression to solve some authentic
problems, but for now we'll just focus on _implementing_ a linear regression
(i.e., writing a program to _find_ the line, given a set of data).

As you might guess, this will be a fairly complicated program, and so, as we
have seen before, we will break it down into smaller pieces first.

<section>Primitives</section>

We'll start by defining some primitives:

<subsection>Sample Mean</subsection>
The _sample mean_ of a set of $N$ values $x_0, x_1, \ldots, x_{N-1}$ is given by:

$$\overline{X} = \frac{1}{N}\sum_{i=0}^{N-1} x_i$$

<subsection>Sample Variance</subsection>
The _sample variance_ of a set of $N$ values $x_0, x_1, \ldots, x_{N-1}$ is given by the following (note the two separate forms):

$$\text{Var}(X) = \frac{1}{N-1}\sum_{i=0}^{N-1} (x_i - \overline{X})^2$$
$$\text{Var}(X) = \frac{1}{N-1}\left(\sum_{i=0}^{N-1}(x_i^2) - \frac{1}{N}\left(\sum_{i=0}^{N-1}x_i\right)^2\right)$$

<subsection>Sample Standard Deviation</subsection>
The _sample standard deviation_ of a set of $N$ values $x_0, x_1, \ldots, x_{N-1}$ is given by:

$$\sigma_X = \sqrt{\text{Var}(X)} = \sqrt{\frac{1}{N-1}\sum_{i=0}^{N-1} (x_i - \overline{X})^2}$$

<subsection>Sample Covariance</subsection>
The _sample covariance_ of two variables $X$ and $Y$ (an estimate of the true underlying covariance of the two variables), each with $N$ samples, such that $y_i$ is associated with $x_i$, is given by the following (note the two separate forms):

$$\text{cov}(X, Y) = \frac{1}{N-1}\sum_{i=0}^{N-1} (x_i-\overline{X})(y_i-\overline{Y})$$
$$\text{cov}(X, Y) = \frac{1}{N-1}\left(\sum_{i=0}^{N-1}(x_iy_i) - \frac{1}{N}\left(\sum_{i=0}^{N-1}x_i\right)\left(\sum_{i=0}^{N-1}y_i\right)\right)$$

<section>Finding the "Best Fit" Line</section>

We would like to find the values $m$ and $b$ for which $y = mx+b$ best approximates the data we've gathered.

Earlier, we said that the line we wanted to find was defined by the values of
$m$ and $b$ that minimized the sum of squared errors between our sampled values
and the values predicted by the line $y=mx+b$:

$$\underset{m, b}{\text{argmin}} \sum_{i=0}^{N-1}\left(y_i - (mx_i + b)\right)^2$$

It is possible to solve for these values, and we will use them our
implementation.  The next section shows a derivation of the solutions for $m$
and $b$.  Understanding the derivation is not crucial for this exercise,
however, and so you are welcome to skip the derivation and move on to
<ref label="results"><a href="{link}">{type} {number}: {title}</a></ref>.

<subsection>Derivation</subsection>

Here, we want to find the values of $m$ and $b$ that minimize the sum of squared error (SSE):

$$\text{SSE} = \sum_{i=0}^{N-1}\left(y_i - (mx_i + b)\right)^2$$

We can use calculus for this: we take the partial derivatives of this
expression with respect to $m$ and $b$, respectively; and set each to 0 (the
function has a minimum where its derivative is 0).

$$\frac{\delta}{\delta b}\text{SSE} = \sum_{i=0}^{N-1} -2(y_i - mx_i - b)$$

$$\frac{\delta}{\delta m}\text{SSE} = \sum_{i=0}^{N-1} -2x_i(y_i - mx_i - b)$$

<subsubsection>Solving for b</subsubsection>

Let's start by considering the partial derivative with respect to $b$.  We want to find when this expression is 0.

$$\sum_{i=0}^{N-1} -2(y_i - mx_i - b) = 0$$

We can start by pulling the constant ($-2$) in front of the summation, and dividing both sides by $-2$:
$$-2 \sum_{i=0}^{N-1} (y_i - mx_i - b) = 0$$
$$\sum_{i=0}^{N-1} (y_i - mx_i - b) = 0$$

And distributing the summation operator:
$$\sum_{i=0}^{N-1} y_i - \sum_{i=0}^{N-1}mx_i - \sum_{i=0}^{N-1}b = 0$$

We can pull the "$m$" and "$b$" constants out of their respective sums:
$$\sum_{i=0}^{N-1} y_i - m\sum_{i=0}^{N-1}x_i - b\sum_{i=0}^{N-1}1 = 0$$

Then we can isolate the "$b$" term by moving it to the right-hand side of the equation:
$$\sum_{i=0}^{N-1} y_i - m\sum_{i=0}^{N-1}x_i = b\sum_{i=0}^{N-1}1$$

And we can evaluate that sum:
$$\sum_{i=0}^{N-1} y_i - m\sum_{i=0}^{N-1}x_i = Nb$$

Then, to solve for $b$, we can divide both sides by $N$:
$$\frac{1}{N}\sum_{i=0}^{N-1} y_i - m\left(\frac{1}{N}\sum_{i=0}^{N-1}x_i\right) = b$$

Notice that the two expressions on the left have the form of our _sample mean_ equation from above, so we know that this must be:
$$\overline{Y} - m\overline{X} = b$$

<subsubsection>Solving for m</subsubsection>

Now we'll consider the partial derivative with respect to $m$, and again set it equal to zero.
$$\sum_{i=0}^{N-1} -2x_i(y_i - mx_i - b) = 0$$

Then we can pull the constant $-2$ out in front of the sum and distribute the $x_i$ across the addition:
$$-2 \sum_{i=0}^{N-1} (x_iy_i - mx_i^2 - bx_i) = 0$$

Again, we can divide both sides by $-2$:
$$\sum_{i=0}^{N-1} (x_iy_i - mx_i^2 - bx_i) = 0$$

And we can distribute the summation operator and move the constants $m$ and $b$ outside the summations:
$$\sum_{i=0}^{N-1}x_iy_i - m\sum_{i=0}^{N-1}x_i^2 - b\sum_{i=0}^{N-1}x_i = 0$$

Next, we substitute in our earlier result for $b$:
$$\sum_{i=0}^{N-1}x_iy_i - m\sum_{i=0}^{N-1}x_i^2 - \left(\frac{1}{N}\sum_{i=0}^{N-1} y_i - m\left(\frac{1}{N}\sum_{i=0}^{N-1}x_i\right)\right)\left(\sum_{i=0}^{N-1}x_i\right) = 0$$

And we distribute the multiplication:
$$\sum_{i=0}^{N-1}x_iy_i - m\sum_{i=0}^{N-1}x_i^2 - \frac{1}{N}\left(\sum_{i=0}^{N-1} y_i\right)\left(\sum_{i=0}^{N-1}x_i\right) + m\left(\frac{1}{N}\sum_{i=0}^{N-1}x_i\right)\left(\sum_{i=0}^{N-1}x_i\right) = 0$$

Then we can move the terms with $m$ in them to the right-hand side of the equation:
$$\sum_{i=0}^{N-1}x_iy_i - \frac{1}{N}\left(\sum_{i=0}^{N-1} y_i\right)\left(\sum_{i=0}^{N-1}x_i\right) = m\sum_{i=0}^{N-1}x_i^2 - m\left(\frac{1}{N}\sum_{i=0}^{N-1}x_i\right)\left(\sum_{i=0}^{N-1}x_i\right)$$

And, to make the next step a _bit_ neater, we can multiply both sides by $N$:
$$N\sum_{i=0}^{N-1}x_iy_i - \left(\sum_{i=0}^{N-1} y_i\right)\left(\sum_{i=0}^{N-1}x_i\right) = mN\sum_{i=0}^{N-1}x_i^2 - m\left(\sum_{i=0}^{N-1}x_i\right)\left(\sum_{i=0}^{N-1}x_i\right)$$

Dividing through to isolate $m$ gives us the following:
$$\frac{\displaystyle{N\sum_{i=0}^{N-1}(x_iy_i) - \left(\sum_{i=0}^{N-1} y_i\right)\left(\sum_{i=0}^{N-1}x_i\right)}}{\displaystyle{N\sum_{i=0}^{N-1}(x_i^2) - \left(\sum_{i=0}^{N-1}x_i\right)^2}} = m$$

Multiplying by ($\frac{1/N}{1/N}$) gets us to a slightly different form:

$$\frac{\displaystyle{\sum_{i=0}^{N-1}(x_iy_i) - \frac{1}{N}\left(\sum_{i=0}^{N-1} y_i\right)\left(\sum_{i=0}^{N-1}x_i\right)}}{\displaystyle{\sum_{i=0}^{N-1}(x_i^2) - \frac{1}{N}\left(\sum_{i=0}^{N-1}x_i\right)^2}} = m$$

Recalling the definitions of _sample variance_ and _sample covariance_, we can see that this is equivalent to:

$$\frac{\text{cov}(X, Y)}{\text{Var}(X)} = m$$

<subsection label="results">Results</subsection>

The analysis above leads us to the following conclusion:

$$m = \frac{\text{cov}(X, Y)}{\text{Var}(X)}$$

and

$$b = \overline{Y} - m\overline{X}$$

Here, the first equation tells us that the slope of the "best fit" line is the
ratio of the covariance of $X$ and $Y$ to the variance of $X$.  The second
tells us that the line must pass through the point $(\overline{X}, \overline{Y})$.

<section>Pearson's R</section>

We will also define the Pearson Correlation Coefficient of two variables $X$ and $Y$ as:

$$r = \frac{\text{cov}(X,Y)}{\sigma_X\sigma_Y}$$

This number $r$, which is between $-1$ and $1$, tells us how strongly, and in what direction, the two variables are correlated: a value of 1 implies total positive linear correlation, 0 implies no linear correlation, and -1 implies total negative linear correlation.

<section>Your Task</section>

Your task in this exercise is to implement several Python functions related to
the discussion above:

* `sample_mean(values)` should take as its lone argument a list of $x$ values, and it should return the sample mean of those values.

* `sample_var(values)` should take a list of $x$ values as its argument, and it should return the sample variance of those values.

* `sample_std(values)` should take a list of $x$ values as its argument, and it should return the sample standard deviation of those values.

* `sample_cov(x_values, y_values)` should take a list of $x$ values and a list of $y$ values as its arguments, and it should return the sample covariance of $X$ and $Y$.

* `pearson_r(x_values, y_values)` should take a list of $x$ values and a list of $y$ values as its arguments, and it should return Pearson's r value for $X$ and $Y$.

* `linear_regression(x_values, y_values)` should take a list of $x$ values and a list of $y$ values as its arguments, and it should return a tuple of three elements, in this order:

    * the slope of the "best-fit" line,
    * the vertical intercept of the "best-fit" line, and
    * the Pearson r value for the regression

**You should implement this code _without the use of `numpy` or `scipy`_.**

You will want to do some testing on your own machine first!  Many explanations
of lineare regression have small examples that are good for testing (for
example, .  You can also try doing a test with values that are exactly on the
same line (what should the $m$, $b$, and $r$ values be in that case?), or on
other small data sets.

In order to keep things organized, you should try to implement these functions
in terms of the others whenever possible!


<section>Submission</section>

<question pythoncode>


csq_interface="upload"
csq_show_skeleton=False

csq_sandbox_options = {'BADIMPORT': {'numpy', 'scipy'}}

import ast
import random

def check_num(x, y):
    try:
        return abs(ast.literal_eval(x)-ast.literal_eval(y)) <= 1e-2
    except:
        return False

csq_tests = [
    {'code': 'values = %r\nans=sample_mean(values)' % [round(random.uniform(-20,10), 2) for i in range(random.randint(8, 25))], 'check_function': check_num} for i in range(3)
]

csq_tests += [
    {'code': 'values = %r\nans=sample_var(values)' % [round(random.uniform(-20,10), 2) for i in range(random.randint(8, 25))], 'check_function': check_num} for i in range(3)
]

csq_tests += [
    {'code': 'values = %r\nans=sample_std(values)' % [round(random.uniform(-20,10), 2) for i in range(random.randint(8, 25))], 'check_function': check_num} for i in range(3)
]



def checkregression(sub, soln):
    try:
        x = ast.literal_eval(sub)
        y = ast.literal_eval(soln)
    except:
        return 0.0
    return len(x[-1]) == len(y[-1]) and all(abs(i-j) <= 1e-2 for i,j in zip(x[-1], y[-1]))

def mfunc(x):
    try:
        x = ast.literal_eval(x)
    except:
        return 'Could not interpret submission: %r' % x
    return '<tt>%r</tt><br/>%s' % (x[-1], make_regress_plot(x[0], x[1], x[2][0], x[2][1]))

csq_covar_tests = []
csq_pearson_tests = []
csq_linreg_tests = []
for i in range(2):
    m = random.uniform(-10,10)
    b = random.uniform(-100,100)
    x = [round(random.uniform(-30,40), 2) for i in range(random.randint(20,200))]
    y = [m*i+b for i in x]
    csq_linreg_tests.append({'code': 'xvals = %r\nyvals = %r\nans = [xvals, yvals, linear_regression(xvals, yvals)]' % (x, y)})
    if i%2:
        csq_covar_tests.append({'code': 'xvals = %r\nyvals = %r\nans = sample_cov(xvals, yvals)' % (x, y)})
        csq_pearson_tests.append({'code': 'xvals = %r\nyvals = %r\nans = pearson_r(xvals, yvals)' % (x, y)})
for i in range(5):
    x = [round(random.uniform(-50,70), 2) for i in range(random.randint(20,200))]
    y = [round(random.uniform(-80,-90), 2) for i in x]
    csq_linreg_tests.append({'code': 'xvals = %r\nyvals = %r\nans = [xvals, yvals, linear_regression(xvals, yvals)]' % (x, y)})
    if i%2:
        csq_covar_tests.append({'code': 'xvals = %r\nyvals = %r\nans = sample_cov(xvals, yvals)' % (x, y)})
        csq_pearson_tests.append({'code': 'xvals = %r\nyvals = %r\nans = pearson_r(xvals, yvals)' % (x, y)})
for i in range(5):
    m = random.uniform(-10,10)
    b = random.uniform(-100,100)
    x = [round(random.uniform(-1000,1000), 2) for i in range(random.randint(20,200))]
    y = [random.gauss(m*i+b, 100) for i in x]
    csq_linreg_tests.append({'code': 'xvals = %r\nyvals = %r\nans = [xvals, yvals, linear_regression(xvals, yvals)]' % (x, y)})
    if i%2:
        csq_covar_tests.append({'code': 'xvals = %r\nyvals = %r\nans = sample_cov(xvals, yvals)' % (x, y)})
        csq_pearson_tests.append({'code': 'xvals = %r\nyvals = %r\nans = pearson_r(xvals, yvals)' % (x, y)})
for i in csq_covar_tests + csq_pearson_tests:
    i['check_function'] = check_num
for i in csq_linreg_tests:
    i['check_function'] = checkregression
    i['transform_output'] = mfunc

csq_tests.extend(csq_covar_tests)
csq_tests.extend(csq_pearson_tests)
csq_tests.extend(csq_linreg_tests)


csq_soln = """def sample_mean(xs):
    return sum(xs) / len(xs)

def sample_var(xs):
    return sample_std(xs)**2

def sample_std(xs):
    m = sample_mean(xs)
    return (sum([(i-m)**2 for i in xs]) / (len(xs)-1))**0.5

def sample_cov(xs, ys):
    x_mean = sample_mean(xs)
    y_mean = sample_mean(ys)
    o = 0.0
    for index in range(len(xs)):
        o += (xs[index] - x_mean)*(ys[index] - y_mean)
    return o / (len(xs) - 1)

def pearson_r(xs, ys):
    return sample_cov(xs, ys) / (sample_std(xs)*sample_std(ys))

def linear_regression(xs, ys):
    r = pearson_r(xs, ys)
    m = r * sample_std(ys) / sample_std(xs)
    b = sample_mean(ys) - m * sample_mean(xs)
    return m, b, r"""
</question>
