/** Indian states and union territories for address forms (dropdown values). */
export const INDIAN_STATES_AND_UTS = [
  'Andaman and Nicobar Islands',
  'Andhra Pradesh',
  'Arunachal Pradesh',
  'Assam',
  'Bihar',
  'Chandigarh',
  'Chhattisgarh',
  'Dadra and Nagar Haveli and Daman and Diu',
  'Delhi',
  'Goa',
  'Gujarat',
  'Haryana',
  'Himachal Pradesh',
  'Jammu and Kashmir',
  'Jharkhand',
  'Karnataka',
  'Kerala',
  'Ladakh',
  'Lakshadweep',
  'Madhya Pradesh',
  'Maharashtra',
  'Manipur',
  'Meghalaya',
  'Mizoram',
  'Nagaland',
  'Odisha',
  'Puducherry',
  'Punjab',
  'Rajasthan',
  'Sikkim',
  'Tamil Nadu',
  'Telangana',
  'Tripura',
  'Uttar Pradesh',
  'Uttarakhand',
  'West Bengal',
];

export function matchIndianState(value) {
  const raw = String(value || '').trim();
  if (!raw) {
    return '';
  }
  const exact = INDIAN_STATES_AND_UTS.find((state) => state.toLowerCase() === raw.toLowerCase());
  if (exact) {
    return exact;
  }
  // Common alias from postal APIs
  if (raw.toLowerCase() === 'orissa') {
    return 'Odisha';
  }
  if (raw.toLowerCase() === 'pondicherry') {
    return 'Puducherry';
  }
  return '';
}
