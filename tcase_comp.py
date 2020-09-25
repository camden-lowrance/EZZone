__author__ = 'camden'
import testcases as tc
import matplotlib.pyplot as plt
import numpy as np
import os

def plt_gvf(gvf_array, filename):
    nzones = np.array([idx + 2 for idx,val in enumerate(gvf_array)])
    gvf_arr = np.array(gvf_array)
    above_zero = np.where(gvf_arr > 0)
    gvf_arr_filt = gvf_arr[above_zero]
    nzones_filt = nzones[above_zero]
    fig, ax = plt.subplots()
    ax.plot(nzones_filt,gvf_arr_filt)
    ax.get_xaxis().set_major_locator(plt.MaxNLocator(integer = True))
    ax.axhline(y = .8, color='r', linestyle = '--')
    ax.scatter(nzones[-1], gvf_arr[-1])
    plt.text(.7,.3,'$GVF = %0.2f$'% round(gvf_arr[-1],2), fontsize=20, ha='center', va='center', transform=ax.transAxes)
    plt.xlabel('Number of Zones', fontsize = 18)
    plt.ylabel('Goodness of Variance Fit', fontsize = 18)
    ax.autoscale(tight = True)
    os.chdir('C://Users//camden//Documents//research//researchDocs//figures//mzone')
    plt.savefig(filename, bbox_inches = 'tight')
    plt.show()
'''   
ec_circ_gvf = tc.ec_circ_mzd()

plt_gvf(ec_circ_gvf, 'ecCircGVF8.jpg')
'''
ec_irreg_gvf = tc.ec_irreg_mzd()
plt_gvf(ec_irreg_gvf,'ecIrregGVF8.jpg')

ec_rect_gvf = tc.ec_rect_mzd()
plt_gvf(ec_rect_gvf,  'ecRectGVF8.jpg')

yield_irreg_gvf = tc.yield_irreg_mzd()
plt_gvf(yield_irreg_gvf, 'yieldIrregGVF8.jpg')

yield_irreg2_gvf = tc.yield_irreg2_mzd()
#plt_gvf(yield_irreg2_gvf,  'yieldIrreg2GVF8.jpg')