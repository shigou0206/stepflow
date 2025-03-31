# quadprog.py

import math

#
# 1) vsmall: 计算一个极小量 epsilon
#   JS 中写成 let epsilon=1.0e-60; do{...} while(...)
#
def compute_vsmall() -> float:
    epsilon = 1.0e-60
    while True:
        epsilon_old = epsilon
        epsilon += epsilon
        tmpa = 1.0 + 0.1 * epsilon
        tmpb = 1.0 + 0.2 * epsilon
        if tmpa > 1.0 and tmpb > 1.0:
            break
        # 如果再也没变大,则跳出
        if epsilon == epsilon_old:
            break
    return epsilon

# 直接在模块级计算(和JS一致)
vsmall = compute_vsmall()

#
# 2) dpofa: Cholesky-like factorization
#   a, lda, n => 1-based indexing in JS
#   这里也将 a 视为 (n+1)x(n+1) Python列表
#
def dpofa(a, lda, n):
    info = n
    for j in range(1, n+1):
        info = j
        s = 0.0
        jm1 = j - 1
        if jm1 < 1:
            s = a[j][j] - s
        else:
            for k in range(1, jm1+1):
                t = a[k][j]
                for i in range(1, k):
                    t -= a[i][j] * a[i][k]
                t /= a[k][k]
                a[k][j] = t
                s += t*t
            s = a[j][j] - s

        if s <= 0.0:
            break
        a[j][j] = math.sqrt(s)
        info = 0
    return info


#
# 3) dpori: 由 dpofa 分解的上三角得到逆
#
def dpori(a, lda, n):
    for k in range(1, n+1):
        a[k][k] = 1.0 / a[k][k]
        t = -a[k][k]
        # dscal(k-1, t, a[1][k], 1)
        for i in range(1, k):
            a[i][k] *= t

        kp1 = k+1
        if n < kp1:
            break
        for j in range(kp1, n+1):
            t = a[k][j]
            a[k][j] = 0.0
            # daxpy(k, t, a[1][k], 1, a[1][j], 1)
            for i in range(1, k+1):
                a[i][j] += t * a[i][k]


#
# 4) dposl: 前后代求解 a^T a x = b
#
def dposl(a, lda, n, b):
    # forward
    for k in range(1, n+1):
        t = 0.0
        for i in range(1, k):
            t += a[i][k] * b[i]
        b[k] = (b[k] - t) / a[k][k]

    # backward
    for kb in range(1, n+1):
        k = n + 1 - kb
        b[k] /= a[k][k]
        t = -b[k]
        for i in range(1, k):
            b[i] += t * a[i][k]


#
# 5) qpgen2: Goldfarb/Idnani 核心
#   全部 1-based indexing, 直接移植 JS
#
def qpgen2(dmat, dvec, fddmat, n,
           sol, lagr, crval,
           amat, bvec, fdamat, q, meq,
           iact, nnact,
           iter_, work, ierr):
    global vsmall

    l1 = 0
    it1 = 0
    nvl = 0
    nact = 0
    temp = 0.0
    sum_ = 0.0
    t1 = 0.0
    tt = 0.0
    gc = 0.0
    gs = 0.0
    nu = 0.0
    t1inf = False
    t2min = False

    r = min(n, q)
    l = 2*n + (r*(r+5))//2 + 2*q + 1

    for i in range(1, n+1):
        work[i] = dvec[i]
    for i in range(n+1, l+1):
        work[i] = 0.0
    for i in range(1, q+1):
        iact[i] = 0
        lagr[i] = 0.0

    # check if ierr[1]==0 => dpofa->dposl->dpori
    if ierr[1] == 0:
        info = dpofa(dmat, fddmat, n)
        if info != 0:
            ierr[1] = 2  # not posdef
            return
        dposl(dmat, fddmat, n, dvec)
        dpori(dmat, fddmat, n)
    else:
        # else
        for j in range(1, n+1):
            sol[j] = 0.0
            for i in range(1, j+1):
                sol[j] += dmat[i][j]* dvec[i]
        for j in range(1, n+1):
            dvec[j] = 0.0
            for i in range(j, n+1):
                dvec[j] += dmat[j][i]* sol[i]

    crval[1] = 0.0
    for j in range(1, n+1):
        sol[j] = dvec[j]
        crval[1] += work[j]*sol[j]
        work[j] = 0.0
        for i in range(j+1, n+1):
            dmat[i][j] = 0.0
    crval[1] = - crval[1]/2.0
    ierr[1] = 0

    iwzv = n
    iwrv = iwzv + n
    iwuv = iwrv + r
    iwrm = iwuv + r + 1
    iwsv = iwrm + (r*(r+1))//2
    iwnbv= iwsv + q

    for i in range(1, q+1):
        sum_ = 0.0
        for j in range(1, n+1):
            sum_ += amat[j][i]*amat[j][i]
        work[iwnbv + i] = math.sqrt(sum_)

    nact = nnact  # use the local var
    iter_[1] = 0
    iter_[2] = 0

    def fnGoto50():
        nonlocal nact,nvl,temp,sum_,t1,tt,gc,gs,nu,t1inf,t2min,it1,l1
        iter_[1] += 1
        nonlocal l
        l = iwsv
        for i in range(1, q+1):
            l += 1
            sum_ = -bvec[i]
            for j in range(1, n+1):
                sum_ += amat[j][i]* sol[j]
            if abs(sum_)< vsmall:
                sum_ = 0.0
            if i> meq:
                work[l] = sum_
            else:
                work[l] = -abs(sum_)
                if sum_>0:
                    for j in range(1, n+1):
                        amat[j][i] = -amat[j][i]
                    bvec[i] = -bvec[i]

        for i in range(1, nact+1):
            work[iwsv + iact[i]] = 0.0

        localnvl = 0
        localtemp = 0.0
        for i in range(1, q+1):
            if work[iwsv + i] < localtemp * work[iwnbv + i]:
                localnvl = i
                localtemp = work[iwsv + i]/ work[iwnbv + i]
        nonlocal nvl
        nvl = localnvl
        temp = localtemp
        if nvl==0:
            for i in range(1, nact+1):
                lagr[iact[i]] = work[iwuv + i]
            return 999
        return 0

    def fnGoto55():
        nonlocal nact,nvl,temp,sum_,t1,tt,gc,gs,nu,t1inf,t2min,it1,l1
        for i in range(1, n+1):
            sum_ = 0.0
            for j in range(1, n+1):
                sum_ += dmat[j][i]* amat[j][nvl]
            work[i] = sum_
        localL = iwzv
        for i in range(1, n+1):
            work[localL + i] = 0.0
        for j in range(nact+1, n+1):
            for i in range(1, n+1):
                work[localL + i] += dmat[i][j]* work[j]

        nonlocal t1inf
        t1inf = True
        nonlocal it1
        localit1 = 0
        for i in range(nact, 0, -1):
            sum_ = work[i]
            local_l = iwrm + (i*(i+3))//2
            local_l1 = local_l - i
            for j in range(i+1, nact+1):
                sum_ -= work[local_l]* work[iwrv + j]
                local_l += j
            sum_ /= work[local_l1]
            work[iwrv + i] = sum_
            if iact[i]<= meq:
                continue
            if sum_<=0:
                continue
            t1inf= False
            localit1= i
        it1 = localit1

        if not t1inf:
            nonlocal t1
            t1 = work[iwuv + it1]/ work[iwrv + it1]
            for i in range(1, nact+1):
                if iact[i]<= meq:
                    continue
                if work[iwrv + i]>0:
                    localtemp = work[iwuv + i]/ work[iwrv + i]
                    if localtemp< t1:
                        t1= localtemp
                        it1= i

        # sumsqr
        sumsqr = 0.0
        for i in range(iwzv+1, iwzv+ n+1):
            sumsqr += work[i]* work[i]
        if abs(sumsqr)<= vsmall:
            if t1inf:
                ierr[1] = 1
                return 999
            for i in range(1, nact+1):
                work[iwuv + i] = work[iwuv + i] - t1* work[iwrv + i]
            work[iwuv + nact + 1] += t1
            return 700
        sum_ = 0.0
        for i in range(1, n+1):
            sum_ += work[iwzv + i]* amat[i][nvl]
        nonlocal tt
        tt = - work[iwsv + nvl]/ sum_
        localt2min = True
        if not t1inf:
            if t1< tt:
                tt= t1
                localt2min= False
        nonlocal t2min
        t2min= localt2min

        for i in range(1, n+1):
            sol[i] += tt* work[iwzv + i]
            if abs(sol[i])< vsmall:
                sol[i] =0.0
        crval[1] += tt* sum_* ( tt/2.0 + work[iwuv + nact+1])
        for i in range(1, nact+1):
            work[iwuv + i] = work[iwuv + i] - tt* work[iwrv + i]
        work[iwuv + nact+1] += tt

        if t2min:
            nonlocal nact
            nact += 1
            iact[nact] = nvl
            local_l = iwrm + ((nact -1)* nact)//2 +1
            for i in range(1, nact):
                work[local_l] = work[i]
                local_l+=1
            if nact== n:
                work[local_l] = work[n]
            else:
                for i in range(n, nact, -1):
                    if work[i]==0:
                        continue
                    # do givens
                    localgc = max(abs(work[i-1]), abs(work[i]))
                    localgs = min(abs(work[i-1]), abs(work[i]))
                    if work[i-1]>=0:
                        localtemp = abs(localgc* math.sqrt(1 + (localgs/localgc)*(localgs/localgc)))
                    else:
                        localtemp = -abs(localgc* math.sqrt(1 + (localgs/localgc)*(localgs/localgc)))
                    localgc = work[i-1]/ localtemp
                    localgs = work[i]/ localtemp
                    if localgc==1:
                        continue
                    if localgc==0:
                        work[i-1] = localgs* localtemp
                        for j in range(1, n+1):
                            localtemp2 = dmat[j][i-1]
                            dmat[j][i-1] = dmat[j][i]
                            dmat[j][i] = localtemp2
                    else:
                        work[i-1] = localtemp
                        nonlocal nu
                        nu = localgs/ (1+ localgc)
                        for j in range(1, n+1):
                            localtemp2 = localgc* dmat[j][i-1] + localgs* dmat[j][i]
                            dmat[j][i] = nu* ( dmat[j][i-1] + localtemp2) - dmat[j][i]
                            dmat[j][i-1] = localtemp2
                work[local_l] = work[nact]
        else:
            sum_ = - bvec[nvl]
            for j in range(1, n+1):
                sum_ += sol[j]* amat[j][nvl]
            if nvl> meq:
                work[iwsv + nvl] = sum_
            else:
                work[iwsv + nvl] = -abs(sum_)
                if sum_>0:
                    for j in range(1, n+1):
                        amat[j][nvl] = -amat[j][nvl]
                    bvec[nvl] = -bvec[nvl]
            return 700
        return 0

    def fnGoto797():
        nonlocal l,l1,it1,nact,temp,nu,gc,gs
        l = iwrm + (it1*(it1+1))//2 +1
        l1_ = l + it1
        if work[l1_]==0:
            return 798
        localgc = max(abs(work[l1_-1]), abs(work[l1_]))
        localgs = min(abs(work[l1_-1]), abs(work[l1_]))
        if work[l1_-1]>=0:
            localtemp = abs(localgc* math.sqrt(1 + (localgs/localgc)*(localgs/localgc)))
        else:
            localtemp = -abs(localgc* math.sqrt(1 + (localgs/localgc)*(localgs/localgc)))
        localgc = work[l1_-1]/ localtemp
        localgs = work[l1_]/ localtemp
        if localgc==1:
            return 798
        if localgc==0:
            for i in range(it1+1, nact+1):
                tmp2 = work[l1_-1]
                work[l1_-1] = work[l1_]
                work[l1_] = tmp2
                l1_ += i
            for i in range(1, n+1):
                tmp2 = dmat[i][it1]
                dmat[i][it1] = dmat[i][it1+1]
                dmat[i][it1+1] = tmp2
        else:
            localnu = localgs/(1+ localgc)
            for i in range(it1+1, nact+1):
                tmp2 = localgc* work[l1_-1] + localgs* work[l1_]
                work[l1_] = localnu* ( work[l1_-1] + tmp2) - work[l1_]
                work[l1_-1] = tmp2
                l1_ += i
            for i in range(1, n+1):
                tmp2 = localgc* dmat[i][it1] + localgs* dmat[i][it1+1]
                dmat[i][it1+1] = localnu* ( dmat[i][it1] + tmp2) - dmat[i][it1+1]
                dmat[i][it1] = tmp2
        return 0

    def fnGoto798():
        nonlocal l,l1,it1
        l1_ = l - it1
        for i in range(1, it1+1):
            work[l1_] = work[l]
            l+=1
            l1_+=1
        work[iwuv + it1] = work[iwuv + it1+1]
        iact[it1] = iact[it1+1]
        nonlocal nact
        it1_ = it1+1
        if it1_< nact:
            return 797
        return 0

    def fnGoto799():
        nonlocal nact
        work[iwuv + nact] = work[iwuv + nact+1]
        work[iwuv + nact+1] = 0
        iact[nact] = 0
        nact-=1
        iter_[2]+=1
        return 0

    while True:
        go = fnGoto50()
        if go==999:
            return
        while True:
            go2 = fnGoto55()
            if go2==0:
                break
            if go2==999:
                return
            if go2==700:
                if it1== nact:
                    fnGoto799()
                else:
                    while True:
                        go3= fnGoto797()
                        go4= fnGoto798()
                        if go4!=797:
                            break
                    fnGoto799()


#
# 6) solveQP
#
def solveQP(Dmat, dvec, Amat, bvec=None, meq=0, factorized=None):
    if factorized is None:
        factorized = [0,0]

    # In JS, we do n = Dmat.length-1, Q = Amat[1].length -1
    # 1-based => in python we keep them as "size n+1"
    # We'll do the same approach: pass in arrays with an unused index=0

    # Check if user passed in arrays that are 1-based
    # If not, we can wrap them or shift them
    # For demonstration, we assume user already prepared them as 1-based length
    # e.g. Dmat = [ None, [None, ...], [None, ...], ... ]
    # This code will require that structure, or manually re-locate them

    # Here we do a minimal approach. We detect lengths
    n = len(Dmat)-1  # 1-based
    q = len(Amat[1]) -1  if len(Amat)>1 else 0

    if bvec is None:
        bvec= [0]*(q+1)
    message = ""

    if (n != len(Dmat[1]) -1):
        message = "Dmat is not symmetric!"
    if (n != len(dvec) -1):
        message = "Dmat and dvec are incompatible!"
    if (n != len(Amat) -1):
        message = "Amat and dvec are incompatible!"
    if (q != len(bvec) -1):
        message = "Amat and bvec are incompatible!"
    if (meq> q) or (meq<0):
        message = "Value of meq is invalid!"

    if message !="":
        return {"message": message}

    iact= [0]*(q+1)
    lagr= [0]*(q+1)
    sol = [0]*(n+1)
    crval= [0]*2  # crval[1] used
    r = min(n, q)
    l = 2*n + (r*(r+5))//2 + 2*q +1
    work= [0]*(l+1)
    iter_= [0]*3
    # nact= 0 # in js code stored in variable

    # call qpgen2
    ierr= [0, factorized[1]]

    qpgen2(Dmat, dvec, n, n, sol, lagr, crval,
           Amat, bvec, n, q, meq,
           iact, 0, iter_,
           work, ierr)

    # check factorized
    if factorized[1]==1:
        message= "constraints are inconsistent, no solution!"
    if factorized[1]==2:
        message= "matrix D in quadratic function is not positive definite!"

    return {
      "solution": sol,
      "Lagrangian": lagr,
      "value": crval,
      "unconstrained_solution": dvec,
      "iterations": iter_,
      "iact": iact,
      "message": message
    }


# Example usage/demo
if __name__=="__main__":
    # define 1-based data
    # for example: Dmat is (n+1)x(n+1), ignoring index 0
    n=3
    # we define an array of length n+1, each is length n+1
    Dmat= [None]*(n+1)
    for i in range(n+1):
        if i==0:
            Dmat[i]= None
        else:
            Dmat[i]= [0]*(n+1)

    # fill Dmat, e.g Dmat[1][1], Dmat[1][2], ...
    Dmat[1][1]=1; Dmat[1][2]=0; Dmat[1][3]=0
    Dmat[2][1]=0; Dmat[2][2]=1; Dmat[2][3]=0
    Dmat[3][1]=0; Dmat[3][2]=0; Dmat[3][3]=1

    dvec= [0]*(n+1)
    dvec[1]=0; dvec[2]=5; dvec[3]=0

    # amat (n+1) x (q+1)
    q=3
    Amat= [None]*(n+1)
    for i in range(n+1):
        if i==0:
            Amat[i]= None
        else:
            Amat[i]= [0]*(q+1)
    # fill
    # Amat: [[-4,2,0],[-3,1,-2],[0,0,1]] => 1-based
    Amat[1][1]= -4; Amat[1][2]=2; Amat[1][3]= 0
    Amat[2][1]= -3; Amat[2][2]=1; Amat[2][3]= -2
    Amat[3][1]=  0; Amat[3][2]=0; Amat[3][3]= 1

    bvec= [0]*(q+1)
    bvec[1]= -8; bvec[2]= 2; bvec[3]= 0

    meq=0
    factorized=[0,0]

    result= solveQP(Dmat, dvec, Amat, bvec=bvec, meq=meq, factorized=factorized)

    print("message:", result["message"])
    print("solution:", result["solution"])
    print("value:", result["value"])
    print("unconstrained_solution:", result["unconstrained_solution"])
    print("iterations:", result["iterations"])
    print("iact:", result["iact"])
    print("Lagrangian:", result["Lagrangian"])