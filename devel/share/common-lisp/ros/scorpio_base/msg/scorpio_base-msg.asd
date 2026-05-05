
(cl:in-package :asdf)

(defsystem "scorpio_base-msg"
  :depends-on (:roslisp-msg-protocol :roslisp-utils )
  :components ((:file "_package")
    (:file "CarPwm" :depends-on ("_package_CarPwm"))
    (:file "_package_CarPwm" :depends-on ("_package"))
  ))