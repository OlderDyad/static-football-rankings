import pickle,collections,statistics,math
co,pos,G=pickle.load(open('/tmp/ok_geo.pkl','rb'))
nb=collections.defaultdict(list)
for g in G: nb[g['Home']].append(g); nb[g['Visitor']].append(g)
def km(a,b): return 111*math.hypot(a[0]-b[0],(a[1]-b[1])*math.cos(math.radians(36)))
out=[]
for t,gs in nb.items():
    if not t.endswith('(OK)') or len(gs)<60: continue
    ops=[(g['Visitor'] if g['Home']==t else g['Home']) for g in gs]
    op=[pos[n] for n in ops if n in pos]
    if len(op)<30: continue
    cen=(statistics.median(a for a,b in op),statistics.median(b for a,b in op))
    far=[n for n in ops if n in pos and km(pos[n],cen)>280]
    if len(far)>=10:
        st=collections.Counter(n[-3:-1] for n in far)
        out.append((len(far),len(gs),t,st.most_common(3),collections.Counter(far).most_common(4)))
for o in sorted(out,reverse=True)[:45]: print(o)
