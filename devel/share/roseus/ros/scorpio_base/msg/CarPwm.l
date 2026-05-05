;; Auto-generated. Do not edit!


(when (boundp 'scorpio_base::CarPwm)
  (if (not (find-package "SCORPIO_BASE"))
    (make-package "SCORPIO_BASE"))
  (shadow 'CarPwm (find-package "SCORPIO_BASE")))
(unless (find-package "SCORPIO_BASE::CARPWM")
  (make-package "SCORPIO_BASE::CARPWM"))

(in-package "ROS")
;;//! \htmlinclude CarPwm.msg.html


(defclass scorpio_base::CarPwm
  :super ros::object
  :slots (_pwml _pwma ))

(defmethod scorpio_base::CarPwm
  (:init
   (&key
    ((:pwml __pwml) 0)
    ((:pwma __pwma) 0)
    )
   (send-super :init)
   (setq _pwml (round __pwml))
   (setq _pwma (round __pwma))
   self)
  (:pwml
   (&optional __pwml)
   (if __pwml (setq _pwml __pwml)) _pwml)
  (:pwma
   (&optional __pwma)
   (if __pwma (setq _pwma __pwma)) _pwma)
  (:serialization-length
   ()
   (+
    ;; int32 _pwml
    4
    ;; int32 _pwma
    4
    ))
  (:serialize
   (&optional strm)
   (let ((s (if strm strm
              (make-string-output-stream (send self :serialization-length)))))
     ;; int32 _pwml
       (write-long _pwml s)
     ;; int32 _pwma
       (write-long _pwma s)
     ;;
     (if (null strm) (get-output-stream-string s))))
  (:deserialize
   (buf &optional (ptr- 0))
   ;; int32 _pwml
     (setq _pwml (sys::peek buf ptr- :integer)) (incf ptr- 4)
   ;; int32 _pwma
     (setq _pwma (sys::peek buf ptr- :integer)) (incf ptr- 4)
   ;;
   self)
  )

(setf (get scorpio_base::CarPwm :md5sum-) "55b251c0b3ce40f84dd141bc38bb4783")
(setf (get scorpio_base::CarPwm :datatype-) "scorpio_base/CarPwm")
(setf (get scorpio_base::CarPwm :definition-)
      "int32 pwml
int32 pwma

")



(provide :scorpio_base/CarPwm "55b251c0b3ce40f84dd141bc38bb4783")


