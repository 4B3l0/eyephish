from PIL import Image, ImageDraw, ImageFont, ImageFilter
import cv2
import numpy
import operator
import argparse
import pythonwhois

###############
# -phar
##############

DIALECTS = {
"latin":			(0x0000,0x007f),
"cyrillic":			(0x0400,0x04ff),
"greek":			(0x0370,0x03ff),
"armenian":			(0x0530,0x058f),
"hebrew":			(0x0590,0x05ff),
"arabic":			(0x0600,0x06ff),
"cherokee":         (0x13a0,0x13ff),
"kanji":			(0x4E00,0x9FBF),
"hiragana":			(0x3040,0x309F),
"katakana":			(0x30A0,0x30FF),
"bopomofo":			(0x3100,0x312f),
"thai":				(0x0e00,0xe7f)


}




def homograph_score(im1, im2):
	im3 = cv2.absdiff(im1,im2)
	#cv2.imshow("Keypoints", im1)
	#cv2.imshow("Keypoints2", im2)
	#cv2.imshow("Keypoints3", im3)
	#cv2.waitKey(200)
	score =  im3.sum()/(im3.shape[0] * im3.shape[1])
	return score


def get_centroidized_unicode_img(testchr,font, fontsize = 16):

	ttf=ImageFont.truetype(font, fontsize)

	testw = 40
	testh = 40

#crap out an image with a charcter in it, in a reasonable location
	im1 = Image.new("RGB", (testh,testw), "white")
	ImageDraw.Draw(im1).text((testh/3,testw/3),testchr, fill='black', font=ttf)
	imx = numpy.array(im1)

#find contours of the image we place
	imgray = cv2.cvtColor(imx,cv2.COLOR_BGR2GRAY)
	ret,thresh = cv2.threshold(imgray,127,255,cv2.THRESH_BINARY)
	image, contours,j = cv2.findContours(thresh,cv2.RETR_TREE,cv2.CHAIN_APPROX_SIMPLE)
	im3 = cv2.drawContours(imx, contours[1:], -1, (0,255,0), 1)

#calculate the centroid of all the marks making up the charcter
	cxx = []
	cxy = []
	for c in contours[1:]:
		M = cv2.moments(c)
		try:
			cxx.append(int(M['m10']/M['m00']))
			cxy.append(int(M['m01']/M['m00']))
		except:
#			cv2.imshow("booo", numpy.array(imx))
#			cv2.waitKey(100)
			pass

	if  len(cxx):
		cx = sum(cxx) / len(cxx)
	else:
		cx = 0
	if  len(cxy):
		cy = sum(cxy) / len(cxy)
	else:
		cy = 0
	cx =  (40/2) - (cx - (testw/3))
	cy = (40/2) - (cy - (testh/3))

#recreate the image with the character now centered
	im1 = Image.new("RGB",  (testh,testw), "white")
#	ImageDraw.Draw(im1).text((cx,cy),testchr, fill='black', font=ttf) #X and Y
	ImageDraw.Draw(im1).text((cx,0),testchr, fill='black', font=ttf) #X only

	return numpy.array(im1)


def create_substitution(result, word_end, substitutions):
	# result = {word,buf_modif,score}
	#print result
	if word_end == "":
		return [result]
	else:
		list = []
		if word_end[0] in substitutions:
			for i in substitutions[word_end[0]]:
				newletter = i[0]
				newscore = i[1]
				if result != {}:
					newresult = {"word": result["word"]+newletter, "modif": result["modif"]+[newletter],"score": max(result["score"],newscore)}
				else:
					newresult = {"word": newletter, "modif": [newletter],"score": newscore}
				list += (create_substitution(newresult,word_end[1:],substitutions))
		if result != {}:
			newresult = {"word": result["word"]+word_end[0], "modif": result["modif"]+[" "],"score": result["score"]}
		else:
			newresult = {"word": word_end[0], "modif": [" "],"score": -1}
		list += (create_substitution(newresult,word_end[1:],substitutions))
	return list

def is_domain_available(domain):
	whois = pythonwhois.get_whois(domain)
	return not("id" in whois)

if __name__ == "__main__":
	parser = argparse.ArgumentParser()
	parser.add_argument("--inputdomain",type=str, help="domain you would like to generate look-a-likes for, can be unicode",required=True)
	parser.add_argument("--threshold", default=5, type=float, help="set the visual match threshold, lower is a better match")
	parser.add_argument("--dialect", type=str, help="which unicode tableset to look to generation from (%s)" % ",".join(DIALECTS),required=True)
	parser.add_argument("--font",default = "fonts/Arial.ttf", type=str, help="font to use, Arial,Tahoma for browsers")
	parser.add_argument('--check_availability', action='store_true')
	args = parser.parse_args()

	newstring = []
	stringoptions = {}
	shortdomain = ".".join(args.inputdomain.split(".")[0:-1])
	tld = args.inputdomain.split(".")[-1]
	for i in shortdomain:
		if i not in stringoptions:
			im1 = get_centroidized_unicode_img(i,args.font)
			hscores = {}
			thistring = []
			
			for e in xrange(DIALECTS[args.dialect][0],DIALECTS[args.dialect][1]):
				im2 = get_centroidized_unicode_img(unichr(e),args.font)
				hscores[unichr(e)] = homograph_score(im1, im2)

			sortedhscores = sorted(hscores.items(), key=operator.itemgetter(1))
			for score in sortedhscores:
				if score[1] < args.threshold:
					thistring.append(score)
				else:
					break
			stringoptions[i] = thistring

	newlist = create_substitution({},shortdomain, stringoptions)

	sorted_list = [(dict_["score"],dict_) for dict_ in newlist]
	sorted_list.sort()
	sorted_list = [dict_ for (key, dict_) in sorted_list] 

	if args.check_availability:
		for i in sorted_list:
			domain = i["word"]+"."+tld
			if(is_domain_available(domain)):
				print '\033[92mAVAILABLE\033[0m', domain, i["modif"]
			else:
				print '\033[91mUNAVAILABLE\033[0m', domain, i["modif"]
	else:
		for i in sorted_list:
			domain = i["word"]+"."+tld
			print domain, i["modif"]

