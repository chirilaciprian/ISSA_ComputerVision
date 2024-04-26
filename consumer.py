import cv2
import object_socket
import numpy as np

s = object_socket.ObjectReceiverSocket('127.0.0.1', 5000, print_when_connecting_to_sender=True, print_when_receiving_object=True)

def select_road(frame):
        
    trapezoid = np.zeros((height, width), dtype='uint8')
    cv2.fillConvexPoly(trapezoid, trapezoid_points, 1)
    road_frame = trapezoid*frame
    return trapezoid, road_frame

def top_down_view(frame):
    magical_matrix = cv2.getPerspectiveTransform(np.float32(trapezoid_points), screen_coordinates)
    sterched_frame = cv2.warpPerspective(frame, magical_matrix, (width, height))
    return sterched_frame

def sobel_filter(frame):
    sobel_vertical = np.float32([
        [-1,-2,-1],
        [0,0,0],
        [1,2,1]
        ])
    sobel_horizontal = np.transpose(sobel_vertical)
    f_frame = np.float32(frame)
    frame1 = cv2.filter2D(f_frame, -1, sobel_vertical)
    frame2 = cv2.filter2D(f_frame, -1, sobel_horizontal)
    frame3 = np.sqrt(frame1**2 + frame2**2)
    sobel_frame = cv2.convertScaleAbs(frame3)
    return sobel_frame




while True:
    ret, frame = s.recv_object()
    if not ret:
        break

    # Exercitiul 1
    # cv2.imshow('Frame', frame)

    # Exercitiul 2

    small_frame_width = frame.shape[1]/2.5
    small_frame_height = frame.shape[0]/2.5
    small_frame = cv2.resize(frame, (int(small_frame_width), int(small_frame_height)))
    cv2.imshow('Small Frame', small_frame)
    
    width = small_frame.shape[1]
    height = small_frame.shape[0]
    # Exercitiul 3
    gray_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2GRAY)
    cv2.imshow('Gray Frame', gray_frame)

    # Exercitiul 4
    upper_left = (int(width*0.45),int(height*0.75))
    upper_right = (int(width*0.55),int(height*0.75))
    lower_left = (int(0),int(height))
    lower_right = (int(width),int(height))
    trapezoid_points = np.array([upper_left, upper_right, lower_right, lower_left], dtype='int32')
    screen_coordinates = np.array([[0,0],[width,0],[width,height],[0,height]], dtype='float32')
    trapezoid,road_frame = select_road(gray_frame)
    cv2.imshow('Road Frame', road_frame)

    # Exercitiul 5
    top_down_matrix = top_down_view(road_frame)
    cv2.imshow("Top Down",top_down_matrix)

    # Exercitiul 6
    blured_frame = cv2.blur(top_down_matrix, ksize=(3,3))
    cv2.imshow("Blured",blured_frame)

    # Exercitiul 7
    sobel_frame = sobel_filter(blured_frame)
    cv2.imshow("Sobel",sobel_frame)

    # Exercitiul 8
    treshhold = int(255/2)
    binary_frame = np.array(sobel_frame>treshhold, dtype='uint8')*255
    cv2.imshow("Binary",binary_frame)

    # Exercitiul 9
    no_noise = binary_frame.copy()
    margin = width * 0.05
    no_noise[0:height, 0:int(margin)] = 0
    no_noise[0:height, int(width - margin):width] = 0    
    left_xs = []
    left_ys = []
    right_xs = []
    right_ys = []
    half = int(width / 2)
    left_half = no_noise[0:height, 0:half]
    right_half = no_noise[0:height, half:width]
    left_points = np.argwhere(left_half>0)
    right_points = np.argwhere(right_half>0)
    for point in left_points:
        left_xs.append(point[1])
        left_ys.append(point[0])
    for point in right_points:
        right_xs.append(point[1]+half)
        right_ys.append(point[0])    
    # cv2.imshow("No Noise",no_noise)

    # Exercitiul 10
    lines_frame = no_noise.copy()
    cv2.line(lines_frame,(half,0),(half,height),(100,0,0),2)
    b_left , a_left = np.polynomial.polynomial.polyfit(left_xs,left_ys,deg=1)
    b_right , a_right = np.polynomial.polynomial.polyfit(right_xs,right_ys,deg=1)

    left_top_y = int(0)
    left_top_x = int((left_top_y - b_left) / a_left)
    left_bottom_y = int(height - 1)
    left_bottom_x = int((left_bottom_y - b_left) / a_left)
    right_top_y = int(0)
    right_top_x = int((right_top_y - b_right) / a_right)
    right_bottom_y = int(height - 1)
    right_bottom_x = int((right_bottom_y - b_right) / a_right)

    if np.abs(left_top_x) < 10 ** 8 and np.abs(left_bottom_x) < 10 ** 8:
        left_top = (left_top_x, left_top_y)
        left_bottom = (left_bottom_x, left_bottom_y)
    if np.abs(right_top_x) < 10 ** 8 and np.abs(right_bottom_x) < 10 ** 8:
        right_top = (right_top_x, right_top_y)
        right_bottom = (right_bottom_x, right_bottom_y)

    # Draw the lines
    cv2.line(lines_frame,left_top,left_bottom,(200,0,0),5)
    cv2.line(lines_frame,right_top,right_bottom,(100,0,0),5)
    cv2.imshow("Lines",lines_frame)

     #Exercise 11
    blank_frame_left = np.zeros((height,width),dtype='uint8')
    blank_frame_right = np.zeros((height,width),dtype='uint8')
    cv2.line(blank_frame_left,left_top,left_bottom,(255,0,0),3)
    cv2.line(blank_frame_right,right_top,right_bottom,(255,0,0),3)    

    back_magic_matrix = cv2.getPerspectiveTransform(screen_coordinates, np.float32(trapezoid_points))
    reverted_left_line = cv2.warpPerspective(blank_frame_left, back_magic_matrix, (width, height))
    reverted_right_line = cv2.warpPerspective(blank_frame_right, back_magic_matrix, (width, height))

    left_white_points = np.array(np.argwhere(reverted_left_line > 1))
    right_white_points = np.array(np.argwhere(reverted_right_line > 1))
    colored_image = small_frame.copy()
    for y,x in left_white_points:
        colored_image[y,x] = [0,0,255]
    for y,x in right_white_points:
        colored_image[y,x] = [255,0,0]
    cv2.imshow("Final",colored_image)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break



cv2.destroyAllWindows()

