release: server.json
	zip -r ../udi-russound-poly * -x testcode\* \*__pycache__\* decoding\* ddd logs\* notes.txt Makefile
