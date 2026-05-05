; Auto-generated. Do not edit!


(cl:in-package scorpio_base-msg)


;//! \htmlinclude CarPwm.msg.html

(cl:defclass <CarPwm> (roslisp-msg-protocol:ros-message)
  ((pwml
    :reader pwml
    :initarg :pwml
    :type cl:integer
    :initform 0)
   (pwma
    :reader pwma
    :initarg :pwma
    :type cl:integer
    :initform 0))
)

(cl:defclass CarPwm (<CarPwm>)
  ())

(cl:defmethod cl:initialize-instance :after ((m <CarPwm>) cl:&rest args)
  (cl:declare (cl:ignorable args))
  (cl:unless (cl:typep m 'CarPwm)
    (roslisp-msg-protocol:msg-deprecation-warning "using old message class name scorpio_base-msg:<CarPwm> is deprecated: use scorpio_base-msg:CarPwm instead.")))

(cl:ensure-generic-function 'pwml-val :lambda-list '(m))
(cl:defmethod pwml-val ((m <CarPwm>))
  (roslisp-msg-protocol:msg-deprecation-warning "Using old-style slot reader scorpio_base-msg:pwml-val is deprecated.  Use scorpio_base-msg:pwml instead.")
  (pwml m))

(cl:ensure-generic-function 'pwma-val :lambda-list '(m))
(cl:defmethod pwma-val ((m <CarPwm>))
  (roslisp-msg-protocol:msg-deprecation-warning "Using old-style slot reader scorpio_base-msg:pwma-val is deprecated.  Use scorpio_base-msg:pwma instead.")
  (pwma m))
(cl:defmethod roslisp-msg-protocol:serialize ((msg <CarPwm>) ostream)
  "Serializes a message object of type '<CarPwm>"
  (cl:let* ((signed (cl:slot-value msg 'pwml)) (unsigned (cl:if (cl:< signed 0) (cl:+ signed 4294967296) signed)))
    (cl:write-byte (cl:ldb (cl:byte 8 0) unsigned) ostream)
    (cl:write-byte (cl:ldb (cl:byte 8 8) unsigned) ostream)
    (cl:write-byte (cl:ldb (cl:byte 8 16) unsigned) ostream)
    (cl:write-byte (cl:ldb (cl:byte 8 24) unsigned) ostream)
    )
  (cl:let* ((signed (cl:slot-value msg 'pwma)) (unsigned (cl:if (cl:< signed 0) (cl:+ signed 4294967296) signed)))
    (cl:write-byte (cl:ldb (cl:byte 8 0) unsigned) ostream)
    (cl:write-byte (cl:ldb (cl:byte 8 8) unsigned) ostream)
    (cl:write-byte (cl:ldb (cl:byte 8 16) unsigned) ostream)
    (cl:write-byte (cl:ldb (cl:byte 8 24) unsigned) ostream)
    )
)
(cl:defmethod roslisp-msg-protocol:deserialize ((msg <CarPwm>) istream)
  "Deserializes a message object of type '<CarPwm>"
    (cl:let ((unsigned 0))
      (cl:setf (cl:ldb (cl:byte 8 0) unsigned) (cl:read-byte istream))
      (cl:setf (cl:ldb (cl:byte 8 8) unsigned) (cl:read-byte istream))
      (cl:setf (cl:ldb (cl:byte 8 16) unsigned) (cl:read-byte istream))
      (cl:setf (cl:ldb (cl:byte 8 24) unsigned) (cl:read-byte istream))
      (cl:setf (cl:slot-value msg 'pwml) (cl:if (cl:< unsigned 2147483648) unsigned (cl:- unsigned 4294967296))))
    (cl:let ((unsigned 0))
      (cl:setf (cl:ldb (cl:byte 8 0) unsigned) (cl:read-byte istream))
      (cl:setf (cl:ldb (cl:byte 8 8) unsigned) (cl:read-byte istream))
      (cl:setf (cl:ldb (cl:byte 8 16) unsigned) (cl:read-byte istream))
      (cl:setf (cl:ldb (cl:byte 8 24) unsigned) (cl:read-byte istream))
      (cl:setf (cl:slot-value msg 'pwma) (cl:if (cl:< unsigned 2147483648) unsigned (cl:- unsigned 4294967296))))
  msg
)
(cl:defmethod roslisp-msg-protocol:ros-datatype ((msg (cl:eql '<CarPwm>)))
  "Returns string type for a message object of type '<CarPwm>"
  "scorpio_base/CarPwm")
(cl:defmethod roslisp-msg-protocol:ros-datatype ((msg (cl:eql 'CarPwm)))
  "Returns string type for a message object of type 'CarPwm"
  "scorpio_base/CarPwm")
(cl:defmethod roslisp-msg-protocol:md5sum ((type (cl:eql '<CarPwm>)))
  "Returns md5sum for a message object of type '<CarPwm>"
  "55b251c0b3ce40f84dd141bc38bb4783")
(cl:defmethod roslisp-msg-protocol:md5sum ((type (cl:eql 'CarPwm)))
  "Returns md5sum for a message object of type 'CarPwm"
  "55b251c0b3ce40f84dd141bc38bb4783")
(cl:defmethod roslisp-msg-protocol:message-definition ((type (cl:eql '<CarPwm>)))
  "Returns full string definition for message of type '<CarPwm>"
  (cl:format cl:nil "int32 pwml~%int32 pwma~%~%~%"))
(cl:defmethod roslisp-msg-protocol:message-definition ((type (cl:eql 'CarPwm)))
  "Returns full string definition for message of type 'CarPwm"
  (cl:format cl:nil "int32 pwml~%int32 pwma~%~%~%"))
(cl:defmethod roslisp-msg-protocol:serialization-length ((msg <CarPwm>))
  (cl:+ 0
     4
     4
))
(cl:defmethod roslisp-msg-protocol:ros-message-to-list ((msg <CarPwm>))
  "Converts a ROS message object to a list"
  (cl:list 'CarPwm
    (cl:cons ':pwml (pwml msg))
    (cl:cons ':pwma (pwma msg))
))
