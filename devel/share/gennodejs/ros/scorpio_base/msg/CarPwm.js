// Auto-generated. Do not edit!

// (in-package scorpio_base.msg)


"use strict";

const _serializer = _ros_msg_utils.Serialize;
const _arraySerializer = _serializer.Array;
const _deserializer = _ros_msg_utils.Deserialize;
const _arrayDeserializer = _deserializer.Array;
const _finder = _ros_msg_utils.Find;
const _getByteLength = _ros_msg_utils.getByteLength;

//-----------------------------------------------------------

class CarPwm {
  constructor(initObj={}) {
    if (initObj === null) {
      // initObj === null is a special case for deserialization where we don't initialize fields
      this.pwml = null;
      this.pwma = null;
    }
    else {
      if (initObj.hasOwnProperty('pwml')) {
        this.pwml = initObj.pwml
      }
      else {
        this.pwml = 0;
      }
      if (initObj.hasOwnProperty('pwma')) {
        this.pwma = initObj.pwma
      }
      else {
        this.pwma = 0;
      }
    }
  }

  static serialize(obj, buffer, bufferOffset) {
    // Serializes a message object of type CarPwm
    // Serialize message field [pwml]
    bufferOffset = _serializer.int32(obj.pwml, buffer, bufferOffset);
    // Serialize message field [pwma]
    bufferOffset = _serializer.int32(obj.pwma, buffer, bufferOffset);
    return bufferOffset;
  }

  static deserialize(buffer, bufferOffset=[0]) {
    //deserializes a message object of type CarPwm
    let len;
    let data = new CarPwm(null);
    // Deserialize message field [pwml]
    data.pwml = _deserializer.int32(buffer, bufferOffset);
    // Deserialize message field [pwma]
    data.pwma = _deserializer.int32(buffer, bufferOffset);
    return data;
  }

  static getMessageSize(object) {
    return 8;
  }

  static datatype() {
    // Returns string type for a message object
    return 'scorpio_base/CarPwm';
  }

  static md5sum() {
    //Returns md5sum for a message object
    return '55b251c0b3ce40f84dd141bc38bb4783';
  }

  static messageDefinition() {
    // Returns full string definition for message
    return `
    int32 pwml
    int32 pwma
    
    `;
  }

  static Resolve(msg) {
    // deep-construct a valid message object instance of whatever was passed in
    if (typeof msg !== 'object' || msg === null) {
      msg = {};
    }
    const resolved = new CarPwm(null);
    if (msg.pwml !== undefined) {
      resolved.pwml = msg.pwml;
    }
    else {
      resolved.pwml = 0
    }

    if (msg.pwma !== undefined) {
      resolved.pwma = msg.pwma;
    }
    else {
      resolved.pwma = 0
    }

    return resolved;
    }
};

module.exports = CarPwm;
