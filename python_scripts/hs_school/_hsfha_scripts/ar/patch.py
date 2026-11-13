import pickle
A,B,canon,dom=pickle.load(open('/tmp/ar_hsfha_AB.pkl','rb'))
pickle.dump((A,B,canon,dom),open('/tmp/ar_hsfha_AB.pkl','wb'))
