import pickle
A,B,canon,dom=pickle.load(open('/tmp/la_hsfha_AB.pkl','rb'))
pickle.dump((A,B,canon,dom),open('/tmp/la_hsfha_AB.pkl','wb'))
