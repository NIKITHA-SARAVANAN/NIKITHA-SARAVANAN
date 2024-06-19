r,c=map(int,input().split())
mat=[]
for i in range(r):
    loop=list(map(int,input().split()))
    mat.append(loop)
l=[]
for i in range(r):
    mod=[]
    for j in range(c):
        mod.append(1)
    l.append(mod)    
for i in range(r):
    for j in range(c):
        if(mat[i][j]==0):
            for k in range(c):
                l[i][k]=-1
            for o in range(r):
                l[o][j]=-1
for i in range(r):
    for j in range(c):
        if(l[i][j]==-1):
            print("0",end=" ")
        else:
            print(mat[i][j],end=" ")
    print()        
