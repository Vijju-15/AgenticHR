import { MongoClient } from 'mongodb';

const uri = process.env.MONGODB_URL;

if (!uri) {
  throw new Error('MONGODB_URL environment variable is not set');
}

let clientPromise;

if (process.env.NODE_ENV === 'development') {
  // In dev, reuse client across hot-reloads
  if (!global._mongoClientPromise) {
    const client = new MongoClient(uri);
    global._mongoClientPromise = client.connect();
  }
  clientPromise = global._mongoClientPromise;
} else {
  const client = new MongoClient(uri);
  clientPromise = client.connect();
}

export default clientPromise;
