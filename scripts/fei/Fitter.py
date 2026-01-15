import numpy as np
from scipy.optimize import curve_fit
import matplotlib.pyplot as plt

plt.ion()

def plot_2D_FAMScan_with_gaussFit(pd_reads, center_coords, deltas):
    """
    Three-panel plot:
      [ Raw Data | Fitted Gaussian Model | Residuals ]
    """

    # Coordinate grids
    x_coords = center_coords[0] + deltas
    y_coords = center_coords[1] + deltas
    X, Y = np.meshgrid(x_coords, y_coords, indexing='ij')

    # Execute the 2D Gaussian Fit
    _, popt = fit_gaussian_2d(pd_reads, center_coords, deltas)

    # Fitted model and residuals
    Z_fit = gaussian2d((X, Y), *popt).reshape(X.shape)
    residuals = pd_reads - Z_fit

    # Fitted peak
    x_fit = popt[1]
    y_fit = popt[2]
    z_fit = center_coords[2]

    # Corrected: include offset in fitted peak
    A_peak = gaussian2d((np.array([x_fit]), np.array([y_fit])), *popt)[0]

    # Raw-data max
    max_idx = np.nanargmax(pd_reads)
    ix, iy = np.unravel_index(max_idx, pd_reads.shape)
    A_raw = pd_reads[ix, iy]
    x_raw = X[ix, iy]
    y_raw = Y[ix, iy]
    z_raw = center_coords[2]

    # Format center string
    center_str = f"({center_coords[0]:.4f}, {center_coords[1]:.4f}, {center_coords[2]:.4f})"

    fig, axs = plt.subplots(1, 3, figsize=(17, 5), sharex=True, sharey=True)

    # ---------- Panel 1: Raw Data ----------
    im0 = axs[0].imshow(
        pd_reads.T,
        origin='lower',
        extent=[x_coords[0], x_coords[-1],
                y_coords[0], y_coords[-1]],
        aspect='equal'
    )

    # Mark raw-data max
    axs[0].plot(
        x_raw, y_raw,
        marker='x',
        color='red',
        markersize=8,
        markeredgewidth=2
    )

    raw_txt = (
        f"Max @ ({x_raw:.5f}, {y_raw:.5f}, {z_raw:.5f})\n"
        f"Max = {A_raw:.2f} uW"
    )

    axs[0].text(
        0.02, 0.98, raw_txt,
        transform=axs[0].transAxes,
        verticalalignment='top',
        horizontalalignment='left',
        color='white',
        fontsize=10,
        bbox=dict(facecolor='black', alpha=0.6, edgecolor='none')
    )

    axs[0].set_title(f"2D Coupling\nScan Center = {center_str}")
    axs[0].set_xlabel("X Position (µm)")
    axs[0].set_ylabel("Y Position (µm)")

    cbar0 = plt.colorbar(im0, ax=axs[0])
    cbar0.set_label("Coupling (uW)")

    # ---------- Panel 2: Fitted Model ----------
    im1 = axs[1].imshow(
        Z_fit.T,
        origin='lower',
        extent=[x_coords[0], x_coords[-1],
                y_coords[0], y_coords[-1]],
        aspect='equal'
    )

    # Mark fitted max (small red X)
    axs[1].plot(
        x_fit, y_fit,
        marker='x',
        color='red',
        markersize=8,
        markeredgewidth=2
    )

    fit_txt = (
        f"Max @ ({x_fit:.5f}, {y_fit:.5f}, {z_fit:.5f})\n"
        f"Max = {A_peak:.2f} uW"
    )

    axs[1].text(
        0.02, 0.98, fit_txt,
        transform=axs[1].transAxes,
        verticalalignment='top',
        horizontalalignment='left',
        color='white',
        fontsize=10,
        bbox=dict(facecolor='black', alpha=0.6, edgecolor='none')
    )

    axs[1].set_title("2D Fit")
    axs[1].set_xlabel("X Position (µm)")

    cbar1 = plt.colorbar(im1, ax=axs[1])
    cbar1.set_label("Coupling (uW)")

    # ---------- Panel 3: Residuals ----------
    im2 = axs[2].imshow(
        residuals.T,
        origin='lower',
        extent=[x_coords[0], x_coords[-1],
                y_coords[0], y_coords[-1]],
        aspect='equal'
    )

    axs[2].set_title("Residuals")
    axs[2].set_xlabel("X Position (µm)")

    cbar2 = plt.colorbar(im2, ax=axs[2])
    cbar2.set_label("Residual (uW)")

    plt.tight_layout()

    print(fit_txt)

    peak_coords = (x_fit, y_fit, z_fit)
    return peak_coords, A_peak, popt, fig


def plot_1D_FAMScan_with_gaussFit(pd_reads, center_coords, deltas, show_residuals=False):
    """
    Plot 1D Z scan with overlaid raw data and Gaussian fit.

    Parameters
    ----------
    show_residuals : bool
        If True, include residuals panel.
    """

    # Z coordinates
    z_coords = center_coords[2] + deltas

    # Execute the 1D Gaussian Fit
    _, popt = fit_gaussian_1d(pd_reads, center_coords, deltas)

    # Fitted model and residuals
    Z_fit = gaussian1d(z_coords, *popt)
    residuals = pd_reads - Z_fit

    # Fitted max
    z_fit = popt[1]
    # Corrected: actual peak value including offset
    Z_peak = gaussian1d(z_fit, *popt)

    # Raw-data max
    idx = np.nanargmax(pd_reads)
    #A_raw = pd_reads[idx]
    z_raw = z_coords[idx]
    #x_raw, y_raw = center_coords[0], center_coords[1]

    x0, y0, z0 = center_coords
    center_str = f"({x0:.4f}, {y0:.4f}, {z0:.4f})"

    # Figure layout
    if show_residuals:
        fig, axs = plt.subplots(2, 1, sharex=True)
        ax = axs[0]
    else:
        fig, ax = plt.subplots(1, 1)

    # ---------- Main Plot: Data + Fit ----------
    ax.plot(
        z_coords, pd_reads,
        'o', color='tab:blue', label='Data'
    )

    ax.plot(
        z_coords, Z_fit,
        '-', color='tab:orange', linewidth=2, label='Gaussian Fit'
    )

    # Vertical lines
    ax.axvline(
        z_fit, color='red', linestyle='--', linewidth=1.5,
        label='Fit Max'
    )

    ax.axvline(
        z_raw, color='0.7', linestyle='--', linewidth=1.5,
        label='Measured Max'
    )

    # Annotation (fit) 
    fit_txt = (
        f"Fit Max @ ({x0:.5f}, {y0:.5f}, {z_fit:.5f})\n"
        f"Fit Max = {Z_peak:.2f} uW"
    )

    ax.text(
        0.5, 0.05, fit_txt,             # x=0.5 (middle), y=0.05 (near bottom)
        transform=ax.transAxes,
        va='bottom',                     # align bottom of text box with y position
        ha='center',                     # center horizontally
        fontsize=10,
        bbox=dict(facecolor='grey', alpha=0.9, edgecolor='none')
    )

    ax.set_title(f"Z Focus Scan\nScan Center = {center_str}")
    ax.set_ylabel("Coupling (uW)")
    ax.legend()

    # ---------- Optional Residuals ----------
    if show_residuals:
        axs[1].plot(z_coords, residuals, 'o-', linewidth=1.5)
        axs[1].axhline(0, color='k', linewidth=1)
        axs[1].set_title("Residuals")
        axs[1].set_xlabel("Z Position (µm)")
        axs[1].set_ylabel("Residual (uW)")
    else:
        ax.set_xlabel("Z Position (µm)")

    plt.tight_layout()

    print(fit_txt)

    peak_coords = (x0, y0, z_fit)
    return peak_coords, Z_peak, popt, fig

def gaussian1d(z, A, z0, sigma, offset):
    """
    1D Gaussian with offset.
    """
    return offset + A * np.exp(-0.5 * ((z - z0) / sigma)**2)

def fit_gaussian_1d(pd_reads, center_coords, deltas):
    """
    Fit a 1D Gaussian to a Z scan and return:
        - fitted peak position (z_peak)
        - fitted peak value A_peak
        - popt (all fit parameters)
    """

    # Z positions
    z_coords = center_coords[2] + deltas
    Z = pd_reads.astype(float)

    # Initial guesses
    A0 = np.nanmax(Z)
    z0 = z_coords[np.nanargmax(Z)]
    sigma0 = (z_coords[-1] - z_coords[0]) / 5
    offset0 = np.nanmin(Z)

    p0 = [A0, z0, sigma0, offset0]

    popt, pcov = curve_fit(
        gaussian1d,
        z_coords,
        Z,
        p0=p0,
        maxfev=10000
    )

    A_fit, z_peak, sigma, offset = popt

    return (z_peak, A_fit), popt

def gaussian2d(coords, A, x0, y0, sigma_x, sigma_y, theta, offset):
    """
    2D elliptical Gaussian with rotation.
    coords: (x.ravel(), y.ravel())
    """
    x, y = coords
    xo = x0
    yo = y0

    # Rotation
    a = (np.cos(theta)**2)/(2*sigma_x**2) + (np.sin(theta)**2)/(2*sigma_y**2)
    b = -(np.sin(2*theta))/(4*sigma_x**2) + (np.sin(2*theta))/(4*sigma_y**2)
    c = (np.sin(theta)**2)/(2*sigma_x**2) + (np.cos(theta)**2)/(2*sigma_y**2)

    g = offset + A * np.exp(-(a*(x-xo)**2 + 2*b*(x-xo)*(y-yo) + c*(y-yo)**2))
    return g

def fit_gaussian_2d(pd_reads, center_coords, deltas):
    """
    Fit a 2D Gaussian to the PD scan and return:
        - fitted peak position (x_peak, y_peak)
        - fitted peak value A_peak
        - popt (all fit parameters)
    """

    # Reconstruct actual X,Y coordinate grids
    x_coords = center_coords[0] + deltas
    y_coords = center_coords[1] + deltas
    X, Y = np.meshgrid(x_coords, y_coords, indexing='ij')

    Z = pd_reads.astype(float)

    # Initial guesses
    A0 = np.nanmax(Z)
    (x0_guess, y0_guess) = np.unravel_index(np.nanargmax(Z), Z.shape)
    x0 = X[x0_guess, y0_guess]
    y0 = Y[x0_guess, y0_guess]

    sigma_x0 = (x_coords[-1] - x_coords[0]) / 5
    sigma_y0 = (y_coords[-1] - y_coords[0]) / 5

    theta0 = 0
    offset0 = np.nanmin(Z)

    p0 = [A0, x0, y0, sigma_x0, sigma_y0, theta0, offset0]

    # Fit
    popt, pcov = curve_fit(
        gaussian2d,
        (X.ravel(), Y.ravel()),
        Z.ravel(),
        p0=p0,
        maxfev=10000
    )

    A_fit, x_peak, y_peak, sigx, sigy, theta, offset = popt

    return (x_peak, y_peak, A_fit), popt

'''
pd_reads, center_coords, deltas = redPM_XY(...)
(x_peak, y_peak, A_peak), popt = fit_gaussian_2d(pd_reads, center_coords, deltas)

print("---- Fitted Peak ----")
print(f"X_peak = {x_peak:.6f}")
print(f"Y_peak = {y_peak:.6f}")
print(f"Peak Value = {A_peak:.6f} uW")
'''
