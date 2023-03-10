import numpy as np
from schemes import Mil, Mil_TwoStep, Mil_TwoStep_Antithetic
import time

""" Implementation of Multilevel Monte Carlo """

def MLMC(w0, v0, p_opt, r, kappa, theta, xi, sigma, rho, T, N, epsilon, antithetic):
    
    # Assign schemen to be used on fine grid
    if (antithetic == True):
        TwoStep = Mil_TwoStep_Antithetic
    else:
        TwoStep = Mil_TwoStep
    
    # Calculate constants 
    rho_root = np.sqrt(1 - rho**2)
    A = (theta - sigma ** 2/(4*kappa))
    
    # Step 1
    # Start on level zero, L = 0
    L = 0
    # Keeps track on the paths simulated on each level 
    N_l = np.zeros(1)
    # Keeps track on the sums of differences and sum of squared differences on each level
    sums_l = np.zeros(shape=(4,1))
    # Number of steps per level    
    steps_l = np.ones(1)
    # Keeps track on how many additional paths are needed on each level
    dN_l  = N * np.ones(1)
    # Computational cost
    cost = 0
    
    while np.sum(dN_l) > 0: 
        # Step 2
        for l in range(L+1):
            # Sample new paths if needed
            if dN_l[l] > 0:
                # Number of steps on the fine level
                Mf = 2 ** l
                
                # Step size on the fine level
                hf = T/Mf
                sq_hf = np.sqrt(hf)
                
                # Initialize fine grid
                Wf = w0; Xf = 2 * np.sqrt(v0)
                
                if l == 0:
                    # Sample Wiener increments 
                    dZ1 = np.random.normal(0, sq_hf, size=(int(dN_l[l]),1))
                    dZ2 = np.random.normal(0, sq_hf, size=(int(dN_l[l]),1))
                    
                    Wf = Mil(Wf, Xf, p_opt, r, kappa, theta, xi, sigma, A, rho, rho_root, hf, dZ1[:], dZ2[:])[0]
                    Wc = 0
                    cost += 2*dN_l[l]
                    
                else:
                    # Initialize coarse grid
                    Wc = w0; Xc = 2 * np.sqrt(v0)
                    # Number of steps in the coarse level
                    Mc = int(Mf/2)
                    # Step size on the coarse level
                    hc = T/Mc
                    
                    if antithetic == True:
                        Wf = w0 * np.ones(shape=(int(dN_l[l]),2)); Xf = Xf *  np.ones(shape=(int(dN_l[l]),2))
                        
                    for mc in range(1,Mc+1):
                        
                        # Sample Wiener increments
                        dZ1 = np.random.normal(0, sq_hf, size=(int(dN_l[l]),2))
                        dZ2 = np.random.normal(0, sq_hf, size=(int(dN_l[l]),2))
                    
                        Wf, Xf = TwoStep(Wf, Xf, p_opt, r, kappa, theta, xi, sigma, A, rho, rho_root, hf, dZ1, dZ2)
                    
                        # Reshape Wiener increments such that they fit double step size
                        dZ1 = dZ1.sum(axis=1)
                        dZ2 = dZ2.sum(axis=1)
    
                        Wc, Xc = Mil(Wc, Xc, p_opt, r, kappa, theta, xi, sigma, A, rho, rho_root, hc, dZ1[:], dZ2[:])
                    
                    if antithetic == True:
                        Wf = 0.5 * (Wf[:,0] + Wf[:,1])
                        cost += 2*dN_l[l] * (2*Mf + Mc)
                    else: 
                        cost += 2*dN_l[l] * (Mf + Mc)
                        
                # Update
                N_l[l] += dN_l[l]
                sums_l[0,l] += np.sum(Wf - Wc)
                sums_l[1,l] += np.sum((Wf - Wc) ** 2)
                sums_l[2,l] += np.sum(Wf)
                sums_l[3,l] += np.sum(Wf ** 2)
                     
        # Calculate mean on each level    
        mean_l = sums_l[0, :]/N_l
        # Calculate variance on each level
        V_l = (sums_l[1,:]/(N_l-1) - mean_l**2*(N_l/(N_l-1)))
                
        # Step 3 and step 4
        optimal_N_l = np.ceil(2*epsilon**-2 * np.sqrt(V_l*(T/steps_l)) * np.sum(np.sqrt(V_l*(steps_l/T))))
        
        # Update number of pathes needed on each, we see a maximum on 70k new paths        
        dN_l = np.minimum(np.maximum(optimal_N_l - N_l, 0), 70000)
        if np.sum(dN_l) == 0:
            # Step 5
            # Calculate bias
            if (L >= 2):
                bias = max((((sums_l[0,L-1]/N_l[L-1])/(1-2**1))**2)/2, ((sums_l[0,L]/N_l[L])/(1-2**1))**2)
            # Step 6
            if (L < 2) or (bias > 0.5 *epsilon ** 2):
                L += 1
                N_l = np.append(N_l, 0.0)
                sums_l = np.column_stack([sums_l, [0, 0, 0, 0]])
                steps_l = np.append(steps_l, 2**L)
                dN_l = np.append(dN_l, N)       
               
    # Calculate var on each level
    Var_l = sums_l[3,:]/(N_l-1) - (sums_l[2, :]/N_l)**2*(N_l/(N_l-1))
    
    # Return expectation and standard deviation of terminal wealth 
    EW_T = np.round(np.sum(mean_l),4)
    stdW_T = np.round(np.sqrt(Var_l[L]),4)
    
    return (EW_T, stdW_T, cost, N_l, V_l, Var_l)

if __name__ == "__main__":
    # Final time point
    T = 10
    # Initial wealth
    w0 = 100
    # Initial value of V(T) 
    v0 = 0.0457
    # Riskless interest rate
    r = 0.03
    # Epsilon
    epsilon = 5*10**-2
    # Initial number of paths
    N = 1000
    # Correlation of Wiener processes
    rho = -0.767
    # Kappa
    kappa = 5.07
    # Theta
    theta = 0.0457
    # Xi 
    xi = 1.605
    # Sigma
    sigma = 0.48
    # Optimal control  
    p_opt = 0.1
    
    t_start = time.time()
    print(MLMC(w0, v0, p_opt, r, kappa, theta, xi, sigma, rho, T, N, epsilon, True)[:2])
    t_end= time.time()
    print("\nRun time: ", round(t_end-t_start,5), "sec")
