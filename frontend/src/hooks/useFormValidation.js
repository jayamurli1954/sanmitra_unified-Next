import { useState } from 'react';

/**
 * Custom hook for form validation
 */
export const useFormValidation = (initialValues = {}, validationRules = {}) => {
  const [values, setValues] = useState(initialValues);
  const [errors, setErrors] = useState({});
  const [touched, setTouched] = useState({});

  // Validation rules
  const validate = (fieldName, value) => {
    const rules = validationRules[fieldName];
    if (!rules) return '';

    for (const rule of rules) {
      if (rule.required && (!value || value.toString().trim() === '')) {
        return rule.message || `${fieldName} is required`;
      }
      
      if (rule.minLength && value && value.toString().length < rule.minLength) {
        return rule.message || `${fieldName} must be at least ${rule.minLength} characters`;
      }
      
      if (rule.maxLength && value && value.toString().length > rule.maxLength) {
        return rule.message || `${fieldName} must be at most ${rule.maxLength} characters`;
      }
      
      if (rule.pattern && value && !rule.pattern.test(value)) {
        return rule.message || `${fieldName} is invalid`;
      }
      
      if (rule.min && value && parseFloat(value) < rule.min) {
        return rule.message || `${fieldName} must be at least ${rule.min}`;
      }
      
      if (rule.max && value && parseFloat(value) > rule.max) {
        return rule.message || `${fieldName} must be at most ${rule.max}`;
      }
      
      if (rule.custom && value) {
        const customError = rule.custom(value);
        if (customError) return customError;
      }
    }
    
    return '';
  };

  const handleChange = (fieldName, value) => {
    setValues(prev => ({ ...prev, [fieldName]: value }));
    
    // Validate on change if field has been touched
    if (touched[fieldName]) {
      const error = validate(fieldName, value);
      setErrors(prev => ({ ...prev, [fieldName]: error }));
    }
  };

  const handleBlur = (fieldName) => {
    setTouched(prev => ({ ...prev, [fieldName]: true }));
    const error = validate(fieldName, values[fieldName]);
    setErrors(prev => ({ ...prev, [fieldName]: error }));
  };

  const validateForm = () => {
    const newErrors = {};
    let isValid = true;

    Object.keys(validationRules).forEach(fieldName => {
      const error = validate(fieldName, values[fieldName]);
      if (error) {
        newErrors[fieldName] = error;
        isValid = false;
      }
    });

    setErrors(newErrors);
    setTouched(
      Object.keys(validationRules).reduce((acc, key) => {
        acc[key] = true;
        return acc;
      }, {})
    );

    return isValid;
  };

  const reset = (newValues = initialValues) => {
    setValues(newValues);
    setErrors({});
    setTouched({});
  };

  return {
    values,
    errors,
    touched,
    handleChange,
    handleBlur,
    validateForm,
    reset,
    setValues,
  };
};




